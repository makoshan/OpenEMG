#include "v001_board.hpp"
#include "../mock_inc/stm32l432xx.h"
#include "../mock_inc/nrf.h"

#include <cassert>
#include <cmath>
#include <csetjmp>
#include <csignal>
#include <cstdio>
#include <cstring>
#include <deque>
#include <sys/ucontext.h>
#include <vector>

/* ==================== 1. ARM64 确定性双核协程切换基元 ==================== */
struct FiberCtx {
    uint64_t regs[22];
};

extern "C" void sim_fiber_switch(FiberCtx *from, FiberCtx *to);
__asm__(
    ".globl _sim_fiber_switch\n"
    ".p2align 2\n"
    "_sim_fiber_switch:\n"
    "stp x19, x20, [x0, #0]\n"
    "stp x21, x22, [x0, #16]\n"
    "stp x23, x24, [x0, #32]\n"
    "stp x25, x26, [x0, #48]\n"
    "stp x27, x28, [x0, #64]\n"
    "stp x29, x30, [x0, #80]\n"
    "mov x9, sp\n"
    "str x9, [x0, #96]\n"
    "stp d8, d9, [x0, #112]\n"
    "stp d10, d11, [x0, #128]\n"
    "stp d12, d13, [x0, #144]\n"
    "stp d14, d15, [x0, #160]\n"
    "ldp x19, x20, [x1, #0]\n"
    "ldp x21, x22, [x1, #16]\n"
    "ldp x23, x24, [x1, #32]\n"
    "ldp x25, x26, [x1, #48]\n"
    "ldp x27, x28, [x1, #64]\n"
    "ldp x29, x30, [x1, #80]\n"
    "ldr x9, [x1, #96]\n"
    "mov sp, x9\n"
    "ldp d8, d9, [x1, #112]\n"
    "ldp d10, d11, [x1, #128]\n"
    "ldp d12, d13, [x1, #144]\n"
    "ldp d14, d15, [x1, #160]\n"
    "ret\n"
);

#include "fw_ram_sect.hpp"

/* 由固件编译单元提供的入口钩子 */
extern "C" {
void fw_l432_main_entry(void);
void fw_nrf_main_entry(void);
void fw_l432_systick(void);
void fw_nrf_systick(void);
void fw_copy_rtt_logs(char l432_out[2048], char nrf_out[2048]);
}

static SectSnap g_l432_sects[3] = {
    {"__l432_d", nullptr, nullptr, 0},
    {"__l432_b", nullptr, nullptr, 0},
    {"__l432_c", nullptr, nullptr, 0},
};
static SectSnap g_nrf_sects[3] = {
    {"__nrf_d", nullptr, nullptr, 0},
    {"__nrf_b", nullptr, nullptr, 0},
    {"__nrf_c", nullptr, nullptr, 0},
};

static void fw_restore_l432_ram(void) { restore_sections(g_l432_sects, 3); }
static void fw_restore_nrf_ram(void)  { restore_sections(g_nrf_sects, 3); }
static void fw_register_nrf_static_ptrs(void) { register_sections_for_nrf_dma(g_nrf_sects, 3); }

/* ==================== 2. 全局外设寄存器实例 ==================== */
static constexpr uint64_t SIM_TICKS_PER_US = 64ull; /* 1 tick = 15.625 ns (64 MHz 基准周期) */
static constexpr uint64_t SIM_TICKS_PER_MS = SIM_TICKS_PER_US * 1000ull;

uint32_t       SystemCoreClock     = 16000000u;
uint32_t       nrf_SystemCoreClock = 64000000u;
DWT_Type       g_sim_dwt{};
CoreDebug_Type g_sim_coredebug{};
FLASH_TypeDef  g_sim_flash{};
PWR_TypeDef    g_sim_pwr{};
RCC_TypeDef    g_sim_rcc{};
GPIO_TypeDef   g_sim_gpio[4]{};
SPI_TypeDef    g_sim_spi1{0, 0, {0, &g_sim_spi1}, 0};
SPI_TypeDef    g_sim_spi3{0, 0, {1, &g_sim_spi3}, 0};
I2C_TypeDef    g_sim_i2c1{};

NRF_GPIO_Type  g_sim_nrf_p0{};
NRF_GPIO_Type  g_sim_nrf_p1{};
NRF_UARTE_Type g_sim_nrf_uarte0{};
NRF_SAADC_Type g_sim_nrf_saadc{};
NRF_SPIS_Type  g_sim_nrf_spis1{};
NRF_RADIO_Type g_sim_nrf_radio{};
NRF_FICR_Type  g_sim_nrf_ficr{};
NRF_UICR_Type  g_sim_nrf_uicr{};
NRF_POWER_Type g_sim_nrf_power{};
NRF_NVMC_Type  g_sim_nrf_nvmc{};
NRF_CLOCK_Type g_sim_nrf_clock{};
NRF_TIMER_Type g_sim_nrf_timer2{};

static uint32_t l432_compute_hclk_hz(void);
void SystemCoreClockUpdate(void) { SystemCoreClock = l432_compute_hclk_hz(); }
uint32_t SysTick_Config(uint32_t) { return 0; }
uint32_t nrf_SysTick_Config(uint32_t) { return 0; }

/* ==================== 3. 虚拟硬件孪生核心状态 ==================== */
enum ActiveMcu : int { MCU_HOST = 0, MCU_L432 = 1, MCU_NRF = 2 };

enum AdsSpiState : int {
    ADS_SPI_IDLE = 0,
    ADS_SPI_RREG_CNT,
    ADS_SPI_RREG_DATA,
    ADS_SPI_WREG_CNT,
    ADS_SPI_WREG_DATA,
};

struct VirtualAdsChip {
    bool        present;
    bool        is_1292;
    uint8_t     id_byte;
    uint8_t     regs[0x1A];
    bool        in_rdatac;
    AdsSpiState spi_state;
    uint8_t     cmd_reg;
    uint8_t     cmd_cnt;
    bool        drdy_low;
    uint8_t     shift_buf[27];
    int         shift_pos;
    uint64_t    refbuf_enable_cyc;
    bool        refbuf_enabled;
    uint64_t    pwdn_high_since_cyc;
    uint64_t    pwdn_low_since_cyc;
    bool        vcap1_charged;
    bool        was_reset;
};

struct BleNotifyItem {
    uint8_t  char_suffix; /* 0x02 = DATA, 0x06 = IMU_DATA */
    uint64_t ts_us;
    std::vector<uint8_t> payload;
};

struct PtrRange {
    uint32_t lo32;
    uintptr_t base64;
    size_t size;
};

struct BoardTwinState {
    SimConfig    cfg;
    SimTelemetry tel;

    /* 协程与双核时钟 (16 ticks = 1 µs) */
    FiberCtx     ctx_host;
    FiberCtx     ctx_l432;
    FiberCtx     ctx_nrf;
    ActiveMcu    active_mcu;
    uint64_t     cyc_l432;
    uint64_t     cyc_nrf;
    uint64_t     target_cyc;
    uint64_t     systick_ms_l432;
    uint64_t     systick_ms_nrf;
    uint64_t     timer2_clear_cyc;
    sigjmp_buf   nrf_reset_jmp;
    bool         in_reset_jump;

    /* L432 外设状态 */
    bool         spi_tx_armed[2];
    uint64_t     dwt_offset_cyc;
    uint64_t     next_stall_cyc;

    /* I2C1 <-> LSM6DS3TR-C @ 0x6A */
    uint8_t      imu_regs[0x80];
    uint32_t     i2c_isr;
    uint32_t     i2c_pending_isr;
    uint64_t     i2c_ready_cyc;
    uint8_t      i2c_addr;
    uint8_t      i2c_nbytes;
    uint8_t      i2c_idx;
    bool         i2c_rd;
    bool         i2c_autoend;
    bool         i2c_got_reg;
    uint8_t      i2c_reg_ptr;
    uint64_t     last_imu_sample_cyc;
    uint32_t     imu_sample_seq;

    /* nRF GPIO & SPIS1 */
    uint32_t     nrf_out[2];
    bool         spis_released;
    bool         spis_in_xfer;
    uint32_t     spis_xfer_idx;
    uint8_t     *spis_latched_rx;
    uint32_t     spis_latched_rx_max;
    const uint8_t *spis_latched_tx;
    uint32_t     spis_latched_tx_max;
    std::vector<PtrRange> nrf_ptrs;

    /* 互锁与 PA4 RC 物理电路 */
    uint64_t     ana_en_high_since_cyc;
    bool         prev_ana_en;
    bool         prev_link_cs;
    double       pa4_cap_v;
    uint64_t     pa4_last_cyc;

    /* AFE 双片 / 单片 / 1292 物理模型 */
    VirtualAdsChip chips[2];
    bool         prev_ads_pwdn;
    bool         prev_ads_reset;
    bool         prev_ads_start;
    uint64_t     ads_reset_low_cyc;
    uint64_t     next_drdy_cyc;
    uint64_t     drdy_period_cyc;
    uint64_t     afe_sample_idx;
    uint64_t     prng_state;

    /* S140 BLE GATT 协议栈状态 */
    uint8_t      next_uuid_type;
    uint8_t      uuid_type_to_suffix[16];
    uint16_t     next_attr_handle;
    uint16_t     char_val_handle[8];  /* index by suffix 0x02..0x06 */
    uint16_t     char_cccd_handle[8];
    std::vector<uint8_t> attr_values[64];
    char         adv_dev_name[32];
    bool         ble_connected;
    uint16_t     ble_conn_handle;
    uint16_t     ble_mtu;
    std::deque<ble_evt_t> ble_evt_q;
    std::deque<BleNotifyItem> ble_notify_q;
};

static BoardTwinState B;
alignas(16) static uint8_t g_l432_stack[131072];
alignas(16) static uint8_t g_nrf_stack[131072];
static bool g_sig_installed = false;

/* ==================== 4. nRF52840 Rev3 FICR / APPROTECT 硬件地址拦截 ==================== */
static void segv_mmio_handler(int sig, siginfo_t *si, void *uap) {
    (void)sig;
    ucontext_t *uc = (ucontext_t *)uap;
    uintptr_t addr = (uintptr_t)si->si_addr;
    uint32_t insn = *(const uint32_t *)(uintptr_t)uc->uc_mcontext->__ss.__pc;
    uint32_t rt = insn & 0x1Fu;
    bool is_load = ((insn >> 22) & 1u) != 0;

    auto get_reg = [&](uint32_t r) -> uint64_t {
        if (r < 29) return uc->uc_mcontext->__ss.__x[r];
        if (r == 29) return uc->uc_mcontext->__ss.__fp;
        if (r == 30) return uc->uc_mcontext->__ss.__lr;
        return 0;
    };
    auto set_reg = [&](uint32_t r, uint64_t v) {
        if (r < 29) uc->uc_mcontext->__ss.__x[r] = v;
        else if (r == 29) uc->uc_mcontext->__ss.__fp = v;
        else if (r == 30) uc->uc_mcontext->__ss.__lr = v;
    };

    if (is_load && addr == 0x10000130u) { /* FICR INFO.PART == 0x08 (nRF52840) */
        set_reg(rt, 0x08u);
        uc->uc_mcontext->__ss.__pc += 4;
        return;
    }
    if (is_load && addr == 0x10000134u) { /* FICR INFO.VARIANT == 0x05 (QFAA-F0 Rev3) */
        set_reg(rt, 0x05u);
        uc->uc_mcontext->__ss.__pc += 4;
        return;
    }
    if (!is_load && addr == 0x40000558u) { /* APPROTECT.DISABLE = 0x5A */
        B.tel.approtect_disable_reg = (uint32_t)get_reg(rt);
        uc->uc_mcontext->__ss.__pc += 4;
        return;
    }
    signal(SIGSEGV, SIG_DFL);
    signal(SIGBUS, SIG_DFL);
}

static void ensure_sig_handler() {
    if (g_sig_installed) return;
    struct sigaction sa{};
    sa.sa_sigaction = segv_mmio_handler;
    sa.sa_flags = SA_SIGINFO;
    sigemptyset(&sa.sa_mask);
    sigaction(SIGSEGV, &sa, nullptr);
    sigaction(SIGBUS, &sa, nullptr);
    g_sig_installed = true;
}

void sim_register_nrf_ptr(const volatile void *p, size_t size) {
    uintptr_t b64 = (uintptr_t)p;
    B.nrf_ptrs.push_back(PtrRange{(uint32_t)b64, b64, size});
}

void *sim_resolve_nrf_ptr(uint32_t ptr32) {
    for (const auto &r : B.nrf_ptrs) {
        uint32_t off = ptr32 - r.lo32;
        if ((size_t)off < r.size) {
            return (void *)(r.base64 + (uintptr_t)off);
        }
    }
    return nullptr;
}

/* ==================== 5. 物理互锁网表与高斯噪声/生理信号源 ==================== */
static uint32_t l432_compute_hclk_hz(void) {
    if ((g_sim_rcc.CFGR.val & RCC_CFGR_SWS) == RCC_CFGR_SWS_PLL) {
        uint32_t pllm = ((g_sim_rcc.PLLCFGR & RCC_PLLCFGR_PLLM) >> RCC_PLLCFGR_PLLM_Pos) + 1u;
        uint32_t plln = (g_sim_rcc.PLLCFGR & RCC_PLLCFGR_PLLN) >> RCC_PLLCFGR_PLLN_Pos;
        uint32_t pllr = (((g_sim_rcc.PLLCFGR & RCC_PLLCFGR_PLLR) >> RCC_PLLCFGR_PLLR_Pos) + 1u) * 2u;
        if (plln == 0u) plln = 8u;
        return (16000000u / pllm) * plln / pllr;
    }
    return 16000000u;
}

static uint32_t l432_apb_div(uint32_t ppre) {
    return (ppre < 4u) ? 1u : (1u << (ppre - 3u));
}

static uint32_t l432_pclk1_hz(void) {
    uint32_t ppre1 = (g_sim_rcc.CFGR.val & RCC_CFGR_PPRE1_Msk) >> RCC_CFGR_PPRE1_Pos;
    return l432_compute_hclk_hz() / l432_apb_div(ppre1);
}

static uint32_t l432_pclk2_hz(void) {
    uint32_t ppre2 = (g_sim_rcc.CFGR.val & RCC_CFGR_PPRE2_Msk) >> RCC_CFGR_PPRE2_Pos;
    return l432_compute_hclk_hz() / l432_apb_div(ppre2);
}

static inline uint64_t cpu_ticks(uint64_t mcu_cycles) {
    if (B.active_mcu == MCU_L432) {
        uint32_t hclk = l432_compute_hclk_hz();
        uint64_t mul = (hclk >= 64000000u) ? 1ull : (64000000ull / hclk);
        return mcu_cycles * mul;
    }
    return mcu_cycles; /* nRF52840 @ 64 MHz: 1 cycle = 1 tick */
}

static inline uint64_t active_cyc() {
    return (B.active_mcu == MCU_NRF) ? B.cyc_nrf : B.cyc_l432;
}

static bool compute_oe_n(uint64_t cyc) {
    if (B.cfg.force_oe_n_high) return true;
    bool bench_en = B.cfg.jp701_shorted || ((B.nrf_out[0] >> 0) & 1u);
    bool ilk_trip = B.cfg.vbus_present && !bench_en;
    bool ana_en   = ((g_sim_gpio[2].ODR >> 14) & 1u) != 0; /* PC14 = ANA_EN */
    if (!ana_en || ilk_trip) return true; /* OE_N = 1 (缓冲三态关断) */
    /* EN_RC (R41+C24) 约 2 ms 建立延迟 */
    if (cyc < B.ana_en_high_since_cyc + 2000ull * SIM_TICKS_PER_US) return true;
    return false; /* OE_N = 0 (U16/U19 导通) */
}

static bool compute_afe_3v3_on(uint64_t cyc) {
    bool bench_en = B.cfg.jp701_shorted || ((B.nrf_out[0] >> 0) & 1u);
    bool ilk_trip = B.cfg.vbus_present && !bench_en;
    bool ana_en   = ((g_sim_gpio[2].ODR >> 14) & 1u) != 0;
    (void)cyc;
    return ana_en && !ilk_trip;
}

static double next_gaussian() {
    auto u01 = [&]() -> double {
        B.prng_state = B.prng_state * 6364136223846793005ULL + 1442695040888963407ULL;
        return ((B.prng_state >> 11) + 0.5) * (1.0 / 9007199254740992.0);
    };
    double u1 = u01();
    double u2 = u01();
    if (u1 < 1e-15) u1 = 1e-15;
    return std::sqrt(-2.0 * std::log(u1)) * std::cos(2.0 * M_PI * u2);
}

static void update_pa4_rc(uint64_t cyc) {
    if (cyc <= B.pa4_last_cyc) return;
    double dt_s = (double)(cyc - B.pa4_last_cyc) / (double)(SIM_TICKS_PER_US * 1000000ull);
    B.pa4_last_cyc = cyc;
    if (B.cfg.subboard_kind != SIM_SUBBOARD_ADS1292_2CH) return;

    /* PA4 = GPIOA pin 4: PUPDR 0=NONE, 1=UP(40k->3.3V), 2=DOWN(40k->0V); 外部 R26=100k->3.0V(若 avdd_3v0_ok) + 50pF */
    uint32_t pupd = (g_sim_gpio[0].PUPDR.val >> (4 * 2)) & 3u;
    double g_sum = 0.0, i_sum = 0.0;
    if (pupd == 1u) { g_sum += 1.0 / 40e3; i_sum += 3.3 / 40e3; }
    else if (pupd == 2u) { g_sum += 1.0 / 40e3; }
    if (B.cfg.avdd_3v0_ok && compute_afe_3v3_on(cyc)) {
        g_sum += 1.0 / 100e3;
        i_sum += 3.0 / 100e3;
    }
    if (g_sum > 0.0) {
        double v_inf = i_sum / g_sum;
        double tau = 50e-12 / g_sum;
        B.pa4_cap_v = v_inf + (B.pa4_cap_v - v_inf) * std::exp(-dt_s / tau);
    }
}

static void reset_ads_chip_regs(VirtualAdsChip &c, int idx) {
    std::memset(c.regs, 0, sizeof(c.regs));
    c.regs[0x00] = c.id_byte;
    if (c.is_1292) {
        c.regs[0x01] = 0x02; c.regs[0x02] = 0x80; c.regs[0x04] = 0x01; c.regs[0x05] = 0x01;
        c.regs[0x09] = 0x02; c.regs[0x0A] = 0x01; c.regs[0x0B] = 0x0C;
    } else {
        c.regs[0x01] = 0x06; c.regs[0x02] = 0x40; c.regs[0x03] = 0x40;
        for (int r = 0x05; r <= 0x0C; r++) c.regs[r] = 0x01;
        c.regs[0x14] = 0x0F;
    }
    c.in_rdatac = true; /* TI 手册默认上电/复位进入 RDATAC 模式 */
    c.spi_state = ADS_SPI_IDLE;
    c.drdy_low  = false;
    c.shift_pos = 0;
    c.refbuf_enabled = false;
    c.was_reset = true;
    std::memcpy(B.tel.ads_regs[idx], c.regs, 0x1A);
}

static void check_ads_electrical_hazards(int chip_idx, uint8_t reg, uint8_t val, uint64_t cyc) {
    VirtualAdsChip &c = B.chips[chip_idx];
    if (c.is_1292) {
        if (reg == 0x0B && (val & 0x0Cu) != 0x0Cu) {
            B.tel.hazard_mask |= HAZ_GPIO_OUTPUT_SHORT_GND;
        }
        return;
    }
    /* OpenEMG v0.01 AFE-30P 电气安全死线实时监控 */
    if (reg == 0x01) {
        if (val & 0x20u) B.tel.hazard_mask |= HAZ_ADS1298_CLK_EN_PIN37;
    }
    if (reg == 0x03) {
        if (val & 0x20u) B.tel.hazard_mask |= HAZ_VREF_4V_ON_2V5_RAIL;
        if (val & 0x10u) B.tel.hazard_mask |= HAZ_PIN62_AVDD_RLD_MEAS;
        if ((val & 0x80u) && (val & 0x08u)) B.tel.hazard_mask |= HAZ_RLDREF_INT_SHORT_AGND;
        if ((val & 0x80u) && !c.refbuf_enabled) {
            c.refbuf_enabled = true;
            c.refbuf_enable_cyc = cyc;
        }
        if (val & 0x04u) { /* PD_RLD = 1 */
            if (chip_idx == 1) B.tel.hazard_mask |= HAZ_RLD_NO_WARMUP_OR_U2_RLD;
            if (!c.refbuf_enabled || (cyc - c.refbuf_enable_cyc) < 145000ull * SIM_TICKS_PER_US) {
                B.tel.hazard_mask |= HAZ_RLD_NO_WARMUP_OR_U2_RLD;
            }
        }
    }
    if (reg >= 0x05 && reg <= 0x0C) {
        if ((val & 0x07u) == 0x02u) B.tel.hazard_mask |= HAZ_PIN62_AVDD_RLD_MEAS;
    }
    if (reg == 0x14) {
        /* GPIO1(bit0), GPIO2(bit1), GPIO4(bit3) 在 v0.01 PCB 上硬连 GND，设 0(输出) 即对地短路 */
        if ((val & 0x0Bu) != 0x0Bu) B.tel.hazard_mask |= HAZ_GPIO_OUTPUT_SHORT_GND;
    }
}

static uint64_t current_drdy_period_cyc() {
    const VirtualAdsChip &u1 = B.chips[0];
    if (!u1.present) return 2000ull * SIM_TICKS_PER_US;
    if (u1.is_1292) {
        uint8_t dr = u1.regs[0x01] & 0x07u;
        if (dr == 2u) return 2000ull * SIM_TICKS_PER_US; /* 500 SPS */
        if (dr == 3u) return 1000ull * SIM_TICKS_PER_US; /* 1000 SPS */
        if (dr == 4u) return 500ull * SIM_TICKS_PER_US;  /* 2000 SPS */
        return 2000ull * SIM_TICKS_PER_US;
    } else {
        uint8_t dr = u1.regs[0x01] & 0x07u;
        if (dr == 6u) return 2000ull * SIM_TICKS_PER_US; /* 500 SPS */
        if (dr == 5u) return 1000ull * SIM_TICKS_PER_US; /* 1000 SPS */
        if (dr == 4u) return 500ull * SIM_TICKS_PER_US;  /* 2000 SPS */
        return 2000ull * SIM_TICKS_PER_US;
    }
}

static void synthesize_afe_conversion(uint64_t cyc) {
    (void)cyc;
    uint64_t per = current_drdy_period_cyc();
    double fs_hz = (double)(SIM_TICKS_PER_US * 1000000ull) / (double)per;
    double t_s = (double)B.afe_sample_idx / fs_hz;
    B.afe_sample_idx++;

    /* TI ADS1298 Table 1 输入等效热噪声 (Gain=6, HR=1): 500Hz->1.0uV, 1kHz->1.4uV, 2kHz->2.0uV */
    double sigma_uv = (fs_hz <= 550.0) ? 1.0 : (fs_hz <= 1100.0) ? 1.4 : 2.0;

    /* RLD 闭环开启判据：U1 PD_RLD=1 且 RLD_SENSP!=0 (ADS1298) 或 RLD_SENS=0x23 (ADS1292) */
    bool rld_closed = false;
    if (B.chips[0].is_1292) {
        rld_closed = ((B.chips[0].regs[0x06] & 0x23u) == 0x23u);
    } else {
        rld_closed = ((B.chips[0].regs[0x03] & 0x04u) != 0) && (B.chips[0].regs[0x0D] != 0);
    }

    /* 先生成 16 路电极端真实物理电压 (µV) */
    double elec_uv[16] = {0};
    double raw_src[16] = {0};
    static const double ch_freqs[16] = {
        25.0, 40.0, 62.5, 80.0, 100.0, 125.0, 160.0, 200.0,
        31.25, 55.0, 75.0, 95.0, 115.0, 145.0, 185.0, 240.0
    };
    for (int c = 0; c < 16; c++) {
        if (B.cfg.wave_mode == SIM_WAVE_SINGLE_CH) {
            raw_src[c] = (c == B.cfg.active_single_ch) ? B.cfg.tone_amp_uv * std::sin(2.0 * M_PI * 100.0 * t_s) : 0.0;
        } else if (B.cfg.wave_mode == SIM_WAVE_TONE_SWEEP) {
            raw_src[c] = B.cfg.tone_amp_uv * std::sin(2.0 * M_PI * ch_freqs[c] * t_s);
        } else {
            /* 生理 sEMG 调制包络 (0.2s..0.8s 握拳爆发) + 多谐波肌电成分 */
            double env = (std::fmod(t_s, 1.0) >= 0.15 && std::fmod(t_s, 1.0) <= 0.75) ? 1.0 : 0.05;
            raw_src[c] = env * B.cfg.tone_amp_uv * (
                0.65 * std::sin(2.0 * M_PI * ch_freqs[c] * t_s) +
                0.35 * std::cos(2.0 * M_PI * (ch_freqs[c] * 1.7 + 13.0) * t_s));
        }
    }
    double cm_50hz = B.cfg.mains_50hz_cm_uv * std::sin(2.0 * M_PI * 50.0 * t_s) * (rld_closed ? 0.05 : 1.0);
    for (int c = 0; c < 16; c++) {
        double v = raw_src[c] + cm_50hz;
        if (c > 0)  v += B.cfg.crosstalk_ratio * raw_src[c - 1];
        if (c < 15) v += B.cfg.crosstalk_ratio * raw_src[c + 1];
        elec_uv[c] = v;
    }

    for (int idx = 0; idx < 2; idx++) {
        VirtualAdsChip &chip = B.chips[idx];
        if (!chip.present) continue;
        int nch = chip.is_1292 ? 2 : 8;

        std::memset(chip.shift_buf, 0, sizeof(chip.shift_buf));
        if (chip.is_1292) {
            /* ADS1292 原生状态字: 0xC0 | GPIO=0 */
            chip.shift_buf[0] = 0xC0u; chip.shift_buf[1] = 0x00u; chip.shift_buf[2] = 0x00u;
        } else {
            chip.shift_buf[0] = 0xC0u; chip.shift_buf[1] = 0x00u; chip.shift_buf[2] = 0x00u;
        }

        for (int ch = 0; ch < nch; ch++) {
            uint8_t chset = chip.regs[(chip.is_1292 ? 0x04 : 0x05) + ch];
            bool pd_ch = (chset & 0x80u) != 0;
            static const double k_pga_gain[8] = {6.0, 1.0, 2.0, 3.0, 4.0, 8.0, 12.0, 6.0};
            double ch_gain = k_pga_gain[(chset >> 4) & 0x07u];
            double ch_lsb_uv = chip.is_1292 ? (2.0 * 2.42e6 / ch_gain / 16777215.0)
                                            : (2.0 * 2.40e6 / ch_gain / 16777215.0);
            uint8_t mux = chset & 0x07u;
            double uv = next_gaussian() * sigma_uv;

            if (pd_ch) {
                uv = 0.0;
            } else if (mux == 0x05u) { /* TEST_SIGNAL */
                if (chip.is_1292) {
                    bool int_test = (chip.regs[0x02] & 0x02u) != 0;
                    bool freq_1hz = (chip.regs[0x02] & 0x01u) != 0;
                    if (int_test) {
                        double sign = freq_1hz ? ((std::fmod(t_s, 1.0) < 0.5) ? 1.0 : -1.0) : 1.0;
                        uv += sign * (2420000.0 / 2400.0); /* ±1008.3 µV -> 2016.7 µVpp */
                    }
                } else {
                    /* v0.01 AFE-30P 物理特性：U1.17/18 与 U2.17/18 独立悬空！本片未开 INT_TEST(0x10) 则 0 方波！ */
                    bool int_test = (chip.regs[0x02] & 0x10u) != 0;
                    if (B.cfg.old_u2_cfg2_zero_bug && idx == 1) int_test = false;
                    if (int_test) {
                        double f_test = 2048000.0 / 2097152.0; /* 0.9765625 Hz */
                        double sign = (std::fmod(t_s * f_test, 1.0) < 0.5) ? 1.0 : -1.0;
                        double amp = ((chip.regs[0x02] & 0x04u) ? 2.0 : 1.0) * 1000.0; /* ±1000 µV -> 2000 µVpp */
                        uv += sign * amp;
                    }
                }
            } else if (mux == 0x01u) {
                /* INPUT SHORTED: 仅热噪声 sigma_uv */
            } else if (mux == 0x02u && chip.is_1292) {
                /* ADS1292 RLD_MEASURE */
                uv += rld_closed ? (15.0 * std::sin(2.0 * M_PI * 50.0 * t_s)) : 0.0;
            } else if (mux == 0x00u) {
                uv += elec_uv[idx * 8 + ch];
            }

            long code = std::lround(uv / ch_lsb_uv);
            if (code > 8388607L) code = 8388607L;
            if (code < -8388608L) code = -8388608L;
            uint32_t u24 = (uint32_t)code & 0xFFFFFFu;
            chip.shift_buf[3 + ch * 3 + 0] = (uint8_t)(u24 >> 16);
            chip.shift_buf[3 + ch * 3 + 1] = (uint8_t)(u24 >> 8);
            chip.shift_buf[3 + ch * 3 + 2] = (uint8_t)(u24);
        }
        chip.shift_pos = 0;
        if (!B.cfg.drdy_a_timeout) {
            chip.drdy_low = true;
        }
    }
}

static void step_hardware_to(uint64_t cyc) {
    update_pa4_rc(cyc);

    bool oe_n = compute_oe_n(cyc);
    bool afe_pwr = compute_afe_3v3_on(cyc);
    bool ads_start = !oe_n && (((g_sim_gpio[0].ODR >> 3) & 1u) != 0);
    bool ads_pwdn  = !oe_n && (((g_sim_gpio[0].ODR >> 1) & 1u) != 0);

    if (afe_pwr && ads_pwdn && ads_start && B.chips[0].present) {
        if (!B.prev_ads_start) {
            B.drdy_period_cyc = current_drdy_period_cyc();
            B.next_drdy_cyc = cyc + B.drdy_period_cyc;
        }
        while (cyc >= B.next_drdy_cyc) {
            synthesize_afe_conversion(B.next_drdy_cyc);
            B.next_drdy_cyc += B.drdy_period_cyc;
        }
    }
    B.prev_ads_start = ads_start;

    /* 104 Hz LSM6DS3TR-C 新样本产生 (周期 9615.38 µs = 615385 ticks) */
    if (B.cfg.imu_present && (B.imu_regs[0x10] & 0xF0u) != 0) {
        if (cyc - B.last_imu_sample_cyc >= 615385ull) {
            B.last_imu_sample_cyc = cyc;
            B.imu_regs[0x1E] = 0x07u; /* TDA | GDA | XLDA */
            double t_s = (double)cyc / (double)(SIM_TICKS_PER_US * 1000000ull);
            bool xl_8g = ((B.imu_regs[0x10] >> 2) & 3u) == 3u; /* 0x4C -> ±8g (4096 LSB/g); 0x40 -> ±2g (16393 LSB/g) */
            int16_t gx = (int16_t)std::lround(120.0 * std::sin(2.0 * M_PI * 1.5 * t_s));
            int16_t gy = (int16_t)std::lround(-85.0 * std::cos(2.0 * M_PI * 1.5 * t_s));
            int16_t gz = (int16_t)std::lround(40.0 * std::sin(2.0 * M_PI * 0.75 * t_s));
            int16_t ax = xl_8g ? 48  : 196;
            int16_t ay = xl_8g ? -64 : -262;
            int16_t az = xl_8g ? 4096 : 16384; /* +1.000 g 静止重力 */
            int16_t v6[6] = {gx, gy, gz, ax, ay, az};
            for (int i = 0; i < 6; i++) {
                B.imu_regs[0x22 + 2 * i]     = (uint8_t)((uint16_t)v6[i] & 0xFFu);
                B.imu_regs[0x22 + 2 * i + 1] = (uint8_t)(((uint16_t)v6[i] >> 8) & 0xFFu);
            }
            B.imu_sample_seq++;
        }
    }

    B.tel.sim_time_us     = cyc / SIM_TICKS_PER_US;
    B.tel.l432_hclk_hz    = l432_compute_hclk_hz();
    B.tel.ana_en_level    = ((g_sim_gpio[2].ODR >> 14) & 1u) != 0;
    B.tel.oe_n_level      = oe_n;
    B.tel.ads_pwdn_level  = ((g_sim_gpio[0].ODR >> 1) & 1u) != 0;
    B.tel.ads_reset_level = ((g_sim_gpio[0].ODR >> 8) & 1u) != 0;
    B.tel.ads_start_level = ((g_sim_gpio[0].ODR >> 3) & 1u) != 0;
    B.tel.pwr_hold_level  = ((B.nrf_out[0] >> 5) & 1u) != 0;
    B.tel.led_pin_level   = ((B.nrf_out[0] >> 23) & 1u) != 0;
}

static void advance_active_mcu(uint64_t delta_cyc) {
    if (B.active_mcu == MCU_L432) {
        /* NC-2h CPU 过载停顿注入：当 ADS_START=1 采集中每 25 ms 注入一次指定微秒 CPU 停顿 */
        if (B.cfg.inject_periodic_stall_us > 0 && (((g_sim_gpio[0].ODR >> 3) & 1u) != 0)) {
            if (B.next_stall_cyc == 0) {
                B.next_stall_cyc = B.cyc_l432 + 25000ull * SIM_TICKS_PER_US;
            } else if (B.cyc_l432 >= B.next_stall_cyc) {
                delta_cyc += (uint64_t)B.cfg.inject_periodic_stall_us * SIM_TICKS_PER_US;
                B.next_stall_cyc = B.cyc_l432 + delta_cyc + 25000ull * SIM_TICKS_PER_US;
            }
        }
        B.cyc_l432 += delta_cyc;
        step_hardware_to(B.cyc_l432);
        uint64_t target_ms = B.cyc_l432 / SIM_TICKS_PER_MS;
        while (B.systick_ms_l432 < target_ms) {
            B.systick_ms_l432++;
            fw_l432_systick();
        }
        /* 若 L432 超前 nRF >= 10 µs 或超过本次步进终点，切出协程 */
        if (B.cyc_l432 >= B.target_cyc && B.cyc_nrf >= B.target_cyc) {
            sim_fiber_switch(&B.ctx_l432, &B.ctx_host);
        } else if (B.cyc_l432 > B.cyc_nrf + 10ull * SIM_TICKS_PER_US) {
            B.active_mcu = MCU_NRF;
            sim_fiber_switch(&B.ctx_l432, &B.ctx_nrf);
        }
    } else if (B.active_mcu == MCU_NRF) {
        B.cyc_nrf += delta_cyc;
        step_hardware_to(B.cyc_nrf);
        uint64_t target_ms = B.cyc_nrf / SIM_TICKS_PER_MS;
        while (B.systick_ms_nrf < target_ms) {
            B.systick_ms_nrf++;
            fw_nrf_systick();
        }
        if (B.cyc_l432 >= B.target_cyc && B.cyc_nrf >= B.target_cyc) {
            sim_fiber_switch(&B.ctx_nrf, &B.ctx_host);
        } else if (B.cyc_nrf > B.cyc_l432 + 10ull * SIM_TICKS_PER_US) {
            B.active_mcu = MCU_L432;
            sim_fiber_switch(&B.ctx_nrf, &B.ctx_l432);
        }
    }
}

void sim_loop_poll(void) {
    /* 2 MCU 时钟周期紧凑轮询分支精确步进（64MHz 下 31.25 ns，16MHz 下 125 ns） */
    advance_active_mcu(cpu_ticks(2ull));
}

/* ==================== 6. L432 寄存器钩子实现 ==================== */
uint32_t sim_l432_rcc_cr_write(uint32_t v) {
    if (v & RCC_CR_HSION) v |= RCC_CR_HSIRDY;
    else                  v &= ~RCC_CR_HSIRDY;
    if (v & RCC_CR_PLLON) v |= RCC_CR_PLLRDY;
    else                  v &= ~RCC_CR_PLLRDY;
    return v;
}

uint32_t sim_l432_rcc_cfgr_write(uint32_t v) {
    uint32_t sw = v & RCC_CFGR_SW;
    if (sw == RCC_CFGR_SW_PLL) {
        /* RM0394 表 11：切入 64 MHz PLL 前必须已切入 VOS Range 1 且设置 Flash >= 3 WS */
        bool vos_r1 = ((g_sim_pwr.CR1 & PWR_CR1_VOS) == PWR_CR1_VOS_0);
        bool ws_ok  = ((g_sim_flash.ACR & FLASH_ACR_LATENCY) >= FLASH_ACR_LATENCY_3WS);
        if (!vos_r1 || !ws_ok) {
            B.tel.hazard_mask |= HAZ_L432_PLL_FLASH_WS;
        }
    }
    v = (v & ~RCC_CFGR_SWS) | (sw << 2);
    return v;
}

uint32_t sim_l432_dwt_read(void) {
    advance_active_mcu(cpu_ticks(4ull));
    uint32_t hclk = l432_compute_hclk_hz();
    uint64_t div = (hclk >= 64000000u) ? 1ull : (64000000ull / hclk);
    return (uint32_t)((B.cyc_l432 - B.dwt_offset_cyc) / div);
}

void sim_l432_dwt_write(uint32_t v) {
    uint32_t hclk = l432_compute_hclk_hz();
    uint64_t div = (hclk >= 64000000u) ? 1ull : (64000000ull / hclk);
    B.dwt_offset_cyc = B.cyc_l432 - (uint64_t)v * div;
}

void sim_l432_gpio_cfg_changed(int port_idx) {
    if (port_idx == 0) update_pa4_rc(active_cyc());
}

void sim_l432_gpio_bsrr(int port_idx, uint32_t v) {
    uint32_t set_m = v & 0xFFFFu;
    uint32_t clr_m = (v >> 16) & 0xFFFFu;
    uint32_t old_odr = g_sim_gpio[port_idx].ODR;
    uint32_t new_odr = (old_odr | set_m) & ~clr_m;
    g_sim_gpio[port_idx].ODR = new_odr;
    uint64_t cyc = active_cyc();

    /* PC14 = ANA_EN 边沿追踪 */
    if (port_idx == 2) {
        bool ana_en = ((new_odr >> 14) & 1u) != 0;
        if (ana_en && !B.prev_ana_en) {
            B.ana_en_high_since_cyc = cyc;
        } else if (!ana_en && B.prev_ana_en) {
            if (B.tel.vbus_inject_us > 0 && B.tel.ana_en_off_us == 0) {
                B.tel.ana_en_off_us = cyc / SIM_TICKS_PER_US;
            }
        }
        B.prev_ana_en = ana_en;
    }

    /* GPIOB PB0(CS_A) / PB1(CS_B) 下降沿重置片内 SPI 状态机 */
    if (port_idx == 1 && !compute_oe_n(cyc)) {
        if (((old_odr >> 0) & 1u) && !((new_odr >> 0) & 1u)) {
            B.chips[0].spi_state = ADS_SPI_IDLE;
            B.chips[0].shift_pos = 0;
        }
        if (((old_odr >> 1) & 1u) && !((new_odr >> 1) & 1u)) {
            B.chips[1].spi_state = ADS_SPI_IDLE;
            B.chips[1].shift_pos = 0;
        }
    }

    /* GPIOA PA1(ADS_PWDN), PA8(ADS_RESET), PA15(LINK_CS) 边沿物理模型 */
    if (port_idx == 0) {
        bool oe_n = compute_oe_n(cyc);
        bool pwdn = !oe_n && (((new_odr >> 1) & 1u) != 0);
        bool rst  = !oe_n && (((new_odr >> 8) & 1u) != 0);

        if (pwdn && !B.prev_ads_pwdn) {
            uint64_t low_us = (cyc - B.chips[0].pwdn_low_since_cyc) / SIM_TICKS_PER_US;
            if (B.chips[0].is_1292 && B.chips[0].pwdn_high_since_cyc > 0) {
                if (low_us >= 4000ull) {
                    /* >= 2^9 t_MOD 硬掉电泄放 VCAP1 */
                    B.chips[0].vcap1_charged = false;
                    B.chips[0].pwdn_high_since_cyc = cyc;
                    B.tel.hazard_mask |= HAZ_ADS1292_VCAP1_UNDERTIME;
                } else if (low_us >= 8ull) {
                    /* 20 µs 纯数字复位：检查此前 VCAP1 是否已充够 >= 1000 ms */
                    uint64_t need_vcap_us = B.cfg.force_short_bringup_por ? 1500000ull : 1000000ull;
                    if ((B.chips[0].pwdn_low_since_cyc - B.chips[0].pwdn_high_since_cyc) >= need_vcap_us * SIM_TICKS_PER_US) {
                        B.chips[0].vcap1_charged = true;
                    } else {
                        B.tel.hazard_mask |= HAZ_ADS1292_VCAP1_UNDERTIME;
                    }
                    reset_ads_chip_regs(B.chips[0], 0);
                }
            } else {
                B.chips[0].pwdn_high_since_cyc = cyc;
            }
        } else if (!pwdn && B.prev_ads_pwdn) {
            B.chips[0].pwdn_low_since_cyc = cyc;
        }
        B.prev_ads_pwdn = pwdn;

        if (!rst && B.prev_ads_reset) {
            B.ads_reset_low_cyc = cyc;
        } else if (rst && !B.prev_ads_reset) {
            /* PA8 = ADS_RESET：仅连在 ADS1298 板 (J2.7 在 ADS1292-2ch 板上为 NC！) */
            if ((cyc - B.ads_reset_low_cyc) >= SIM_TICKS_PER_US) {
                for (int i = 0; i < 2; i++) {
                    if (B.chips[i].present && !B.chips[i].is_1292) {
                        reset_ads_chip_regs(B.chips[i], i);
                    }
                }
            }
        }
        B.prev_ads_reset = rst;

        /* PA15 = LINK_CS 对接 nRF SPIS1 CSN */
        bool link_cs = ((new_odr >> 15) & 1u) != 0;
        if (!link_cs && B.prev_link_cs) {
            /* CSN 下降沿：若 SPIS1 处于 RELEASE 态则锁存 DMA 指针 */
            if ((g_sim_nrf_spis1.ENABLE == SPIS_ENABLE_ENABLE_Enabled) && B.spis_released) {
                B.spis_in_xfer        = true;
                B.spis_xfer_idx       = 0;
                B.spis_latched_rx     = (uint8_t *)sim_resolve_nrf_ptr(g_sim_nrf_spis1.RXD.PTR);
                B.spis_latched_rx_max = g_sim_nrf_spis1.RXD.MAXCNT;
                B.spis_latched_tx     = (const uint8_t *)sim_resolve_nrf_ptr(g_sim_nrf_spis1.TXD.PTR);
                B.spis_latched_tx_max = g_sim_nrf_spis1.TXD.MAXCNT;
            } else {
                B.spis_in_xfer = false;
            }
        } else if (link_cs && !B.prev_link_cs) {
            /* CSN 上升沿：完成 SPIS1 帧事务，触发 EVENTS_END 与 SHORTS END_ACQUIRE */
            if (B.spis_in_xfer) {
                uint32_t rx_amt = (B.spis_xfer_idx < B.spis_latched_rx_max) ? B.spis_xfer_idx : B.spis_latched_rx_max;
                uint32_t tx_amt = (B.spis_xfer_idx < B.spis_latched_tx_max) ? B.spis_xfer_idx : B.spis_latched_tx_max;
                g_sim_nrf_spis1.RXD.AMOUNT = rx_amt;
                g_sim_nrf_spis1.TXD.AMOUNT = tx_amt;
                g_sim_nrf_spis1.EVENTS_END = 1u;
                if (g_sim_nrf_spis1.SHORTS & SPIS_SHORTS_END_ACQUIRE_Msk) {
                    B.spis_released = false;
                    g_sim_nrf_spis1.EVENTS_ACQUIRED = 1u;
                }
                if (rx_amt == 97u && B.spis_latched_rx) {
                    std::memcpy(B.tel.last_report_97b, B.spis_latched_rx, 97u);
                    B.tel.has_report_97b = true;
                }
                B.tel.spi3_frames_sent++;
                B.spis_in_xfer = false;
                /* 让 nRF 立即响应刚到达的 SPIS1 帧 */
                if (B.active_mcu == MCU_L432) {
                    if (B.cyc_nrf < B.cyc_l432) B.cyc_nrf = B.cyc_l432;
                    B.active_mcu = MCU_NRF;
                    sim_fiber_switch(&B.ctx_l432, &B.ctx_nrf);
                }
            }
        }
        B.prev_link_cs = link_cs;
    }
    step_hardware_to(cyc);
}

uint32_t sim_l432_gpio_idr(int port_idx) {
    advance_active_mcu(cpu_ticks(4ull));
    uint64_t cyc = active_cyc();
    uint32_t idr = g_sim_gpio[port_idx].ODR;
    bool oe_n = compute_oe_n(cyc);

    if (port_idx == 0) { /* GPIOA */
        /* PA2 = DRDY_A：经 U19 缓冲 + R701(100k) 下拉到 GND！OE_N=1 时 U19 高阻，R701 强拉 PA2=0！ */
        int drdy_a = 0;
        if (!oe_n) {
            drdy_a = (B.chips[0].present && compute_afe_3v3_on(cyc)) ? (B.chips[0].drdy_low ? 0 : 1) : 1;
        }
        idr = (idr & ~(1u << 2)) | ((uint32_t)drdy_a << 2);

        /* PA4 = AFE_DRDY_B（直连不经 U19）：16CH 为 U2.DRDY；8CH/NONE 浮空跟 PUPDR；2CH 为 RC + 3.0V AVDD_SENSE */
        update_pa4_rc(cyc);
        int drdy_b = 0;
        if (B.cfg.subboard_kind == SIM_SUBBOARD_AFE30P_16CH && compute_afe_3v3_on(cyc)) {
            drdy_b = (B.cfg.drdy_b_stuck_low || B.chips[1].drdy_low) ? 0 : 1;
        } else if (B.cfg.subboard_kind == SIM_SUBBOARD_ADS1292_2CH) {
            drdy_b = (B.pa4_cap_v >= 1.65) ? 1 : 0;
        } else {
            uint32_t pupd = (g_sim_gpio[0].PUPDR.val >> (4 * 2)) & 3u;
            drdy_b = (pupd == 1u) ? 1 : 0;
        }
        idr = (idr & ~(1u << 4)) | ((uint32_t)drdy_b << 4);

        /* PA9/PA10 = IMU_SCL / IMU_SDA */
        int i2c_lvl = B.cfg.imu_bus_stuck_low ? 0 : 1;
        idr = (idr & ~((1u << 9) | (1u << 10))) | ((uint32_t)i2c_lvl << 9) | ((uint32_t)i2c_lvl << 10);
    } else if (port_idx == 1) { /* GPIOB */
        /* PB6 = LINK_RDY <- nRF P0.07 */
        int link_rdy = (B.nrf_out[0] >> 7) & 1u;
        idr = (idr & ~(1u << 6)) | ((uint32_t)link_rdy << 6);
    } else if (port_idx == 3) { /* GPIOH */
        /* PH3 = BOOT0：MCU-U9(Y41) 上经 R5 下拉恒为 0！R4U6 旧板上并入 VBUS_SENSE */
        int ph3 = (B.cfg.mainboard_rev == SIM_MAINBOARD_R4U6 && B.cfg.vbus_present) ? 1 : 0;
        idr = (idr & ~(1u << 3)) | ((uint32_t)ph3 << 3);
    }
    return idr;
}

static uint8_t chip_spi_xfer_byte(int idx, uint8_t mosi, uint32_t sclk_hz, uint64_t cyc) {
    VirtualAdsChip &c = B.chips[idx];
    if (!c.present || !compute_afe_3v3_on(cyc)) return 0x00u;
    if (c.is_1292) {
        if (sclk_hz > 20000000u) {
            B.tel.hazard_mask |= HAZ_ADS1292_SPI_TSDECODE;
            return 0xFFu;
        }
        /* TI SBAS502C §6.6 / Fig.59：冷启动 VCAP1 建立 + 2^18*tCLK(512 ms) POR 完成前 SPI 不响应 */
        uint64_t por_us = B.cfg.force_short_bringup_por ? 1500000ull : 512000ull;
        if (B.cfg.strict_ads1292_por && (cyc - B.ana_en_high_since_cyc) < por_us * SIM_TICKS_PER_US) {
            B.tel.hazard_mask |= HAZ_ADS1292_VCAP1_UNDERTIME;
            return 0x00u;
        }
    }
    if (c.in_rdatac) {
        if (mosi == 0x11u && c.shift_pos == 0) {
            c.in_rdatac = false;
            return 0x00u;
        }
        int frame_len = c.is_1292 ? 9 : 27;
        uint8_t out = (c.shift_pos < frame_len) ? c.shift_buf[c.shift_pos] : 0x00u;
        c.shift_pos++;
        return out;
    }

    switch (c.spi_state) {
    case ADS_SPI_IDLE:
        if (mosi == 0x11u) { c.in_rdatac = false; return 0x00u; }
        if (mosi == 0x10u) { c.in_rdatac = true; c.shift_pos = 0; return 0x00u; }
        if ((mosi & 0xE0u) == 0x20u) { c.cmd_reg = mosi & 0x1Fu; c.spi_state = ADS_SPI_RREG_CNT; return 0x00u; }
        if ((mosi & 0xE0u) == 0x40u) { c.cmd_reg = mosi & 0x1Fu; c.spi_state = ADS_SPI_WREG_CNT; return 0x00u; }
        return 0x00u;
    case ADS_SPI_RREG_CNT:
        c.cmd_cnt = (mosi & 0x1Fu) + 1u;
        c.spi_state = ADS_SPI_RREG_DATA;
        return 0x00u;
    case ADS_SPI_RREG_DATA: {
        uint8_t r = c.cmd_reg++;
        uint8_t v = (r < 0x1Au) ? c.regs[r] : 0x00u;
        if (B.cfg.reg_readback_fault && idx == 0 && (r == 0x04u || r == 0x05u)) v ^= 0x01u;
        if (--c.cmd_cnt == 0u) c.spi_state = ADS_SPI_IDLE;
        return v;
    }
    case ADS_SPI_WREG_CNT:
        c.cmd_cnt = (mosi & 0x1Fu) + 1u;
        c.spi_state = ADS_SPI_WREG_DATA;
        return 0x00u;
    case ADS_SPI_WREG_DATA: {
        uint8_t r = c.cmd_reg++;
        uint8_t val = mosi;
        if (B.cfg.inject_hazard_cfg3 && r == 0x03u) val |= (uint8_t)B.cfg.inject_hazard_cfg3;
        if (B.cfg.inject_hazard_gpio && r == 0x14u) val = (uint8_t)B.cfg.inject_hazard_gpio;

        if (r > 0x00u && r < 0x1Au) {
            if (c.is_1292) {
                if (r != 0x08u) {
                    if (r == 0x01u) val &= 0x87u;
                    if (r == 0x02u) val = (val & 0x7Bu) | 0x80u;
                    if (r == 0x0Au) val &= 0x87u;
                    if (r == 0x0Bu) val &= 0x0Cu;
                    c.regs[r] = val;
                }
            } else {
                if (r == 0x02u) val = (val & 0xF7u);        /* SBAS459K 表18: 复位值 0x40，但 bit7:6 可写且手册要求写 00 */
                if (r == 0x03u) val = (val & 0xFEu) | 0x40u; /* SBAS459K 表19: bit6 恒为 1，bit0 RLD_STAT 只读 */
                if (r == 0x14u) val = (val & 0x0Fu); /* GPIO1/2/4 接地，输入读回电平为 0 */
                c.regs[r] = val;
            }
            B.tel.ads_regs[idx][r] = c.regs[r];
            check_ads_electrical_hazards(idx, r, val, cyc);
        }
        if (--c.cmd_cnt == 0u) c.spi_state = ADS_SPI_IDLE;
        return 0x00u;
    }
    }
    return 0x00u;
}

uint32_t sim_l432_spi_sr_read(int spi_idx, volatile uint32_t *dr_mem, uint32_t cr1) {
    if (!B.spi_tx_armed[spi_idx]) {
        B.spi_tx_armed[spi_idx] = true;
        return SPI_SR_TXE;
    }
    B.spi_tx_armed[spi_idx] = false;
    uint8_t mosi = *(volatile uint8_t *)dr_mem;
    uint32_t br = (cr1 >> SPI_CR1_BR_Pos) & 7u;
    uint32_t pclk_hz = (spi_idx == 0) ? l432_pclk2_hz() : l432_pclk1_hz();
    uint32_t sclk_hz = pclk_hz >> (br + 1u);
    if (sclk_hz == 0u) sclk_hz = 1000000u;
    uint64_t byte_cyc = (8ull * SIM_TICKS_PER_US * 1000000ull) / sclk_hz;
    advance_active_mcu(byte_cyc);
    uint64_t cyc = active_cyc();

    uint8_t miso = 0x00u;
    if (spi_idx == 0) { /* SPI1 <-> AFE */
        B.tel.spi1_sclk_hz = sclk_hz;
        if (compute_oe_n(cyc)) {
            /* U16/U19 三态，PA6 经 R702(100k) 下拉读全 0x00 */
            miso = 0x00u;
        } else {
            /* TI SBAS459K 图 60 铁律：共享 SCLK 第 1 个下降沿不论 CS 状态同步清高两片 DRDY！ */
            B.chips[0].drdy_low = false;
            if (B.chips[1].present && !B.cfg.drdy_b_stuck_low) {
                B.chips[1].drdy_low = false;
            }
            bool cs_a = ((g_sim_gpio[1].ODR >> 0) & 1u) == 0;
            bool cs_b = ((g_sim_gpio[1].ODR >> 1) & 1u) == 0;
            if (cs_a && !cs_b) miso = chip_spi_xfer_byte(0, mosi, sclk_hz, cyc);
            else if (cs_b && !cs_a) miso = chip_spi_xfer_byte(1, mosi, sclk_hz, cyc);
            else miso = 0x00u;
        }
    } else { /* SPI3 <-> nRF SPIS1 */
        B.tel.spi3_sclk_hz = sclk_hz;
        if (sclk_hz > 8000000u) {
            B.tel.hazard_mask |= HAZ_SPI3_OVER_8MHZ;
        }
        if (B.spis_in_xfer) {
            uint8_t wire_mosi = mosi;
            if (B.cfg.corrupt_spi3_crc && B.spis_xfer_idx == 10u) {
                wire_mosi ^= 0x01u;
            }
            miso = (B.spis_latched_tx && B.spis_xfer_idx < B.spis_latched_tx_max)
                       ? B.spis_latched_tx[B.spis_xfer_idx]
                       : (uint8_t)g_sim_nrf_spis1.ORC;
            if (B.spis_latched_rx && B.spis_xfer_idx < B.spis_latched_rx_max) {
                B.spis_latched_rx[B.spis_xfer_idx] = wire_mosi;
            }
            B.spis_xfer_idx++;
        } else {
            miso = 0xFFu;
        }
    }

    *(volatile uint8_t *)dr_mem = miso;
    return SPI_SR_RXNE | SPI_SR_TXE;
}

/* ---------- I2C1 <-> LSM6DS3TR-C（真实硬件后台字节移位并发模型） ---------- */
void sim_l432_i2c_cr1_write(uint32_t v) {
    if ((v & I2C_CR1_PE) == 0) {
        B.i2c_isr = 0;
        B.i2c_pending_isr = 0;
        B.i2c_ready_cyc = 0;
    }
}

void sim_l432_i2c_icr_write(uint32_t v) {
    if (v & I2C_ICR_NACKCF) B.i2c_isr &= ~I2C_ISR_NACKF;
    if (v & I2C_ICR_STOPCF) B.i2c_isr &= ~(I2C_ISR_STOPF | I2C_ISR_BUSY);
}

static uint64_t i2c_byte_cyc() {
    /* 0x0010061A @ PCLK1=16MHz => 400 kHz (~22.5 µs = 1440 ticks); 0x00303D5B => 100 kHz (~90 µs = 5760 ticks) */
    uint32_t pclk1 = l432_pclk1_hz();
    uint64_t base = (g_sim_i2c1.TIMINGR == 0x0010061Au) ? (1440ull) : (5760ull);
    return (base * 16000000ull) / (pclk1 ? pclk1 : 16000000u);
}

void sim_l432_i2c_cr2_write(uint32_t v) {
    if (!(v & I2C_CR2_START)) return;
    advance_active_mcu(cpu_ticks(4ull));
    B.i2c_addr    = (uint8_t)((v >> 1) & 0x7Fu);
    B.i2c_nbytes  = (uint8_t)((v >> I2C_CR2_NBYTES_Pos) & 0xFFu);
    B.i2c_rd      = (v & I2C_CR2_RD_WRN) != 0;
    B.i2c_autoend = (v & I2C_CR2_AUTOEND) != 0;
    B.i2c_idx     = 0;

    if (B.cfg.imu_bus_stuck_low) {
        B.i2c_isr = I2C_ISR_BUSY;
        B.i2c_pending_isr = I2C_ISR_BUSY;
        B.i2c_ready_cyc = 0;
        return;
    }
    if (!B.cfg.imu_present || B.i2c_addr != 0x6Au) {
        B.i2c_isr = I2C_ISR_BUSY;
        B.i2c_pending_isr = I2C_ISR_NACKF | I2C_ISR_STOPF;
        B.i2c_ready_cyc = active_cyc() + i2c_byte_cyc();
        return;
    }
    B.i2c_isr = I2C_ISR_BUSY;
    if (B.i2c_rd) {
        /* 读事务：地址帧 + 首字节移入合计 2 个字节窗口后首字节 RXNE 就绪 */
        B.i2c_pending_isr = I2C_ISR_BUSY | I2C_ISR_RXNE;
        B.i2c_ready_cyc = active_cyc() + 2ull * i2c_byte_cyc();
    } else {
        B.i2c_got_reg = false;
        B.i2c_pending_isr = I2C_ISR_BUSY | I2C_ISR_TXIS;
        B.i2c_ready_cyc = active_cyc() + i2c_byte_cyc();
    }
}

void sim_l432_i2c_txdr_write(uint32_t v) {
    advance_active_mcu(cpu_ticks(4ull));
    if (!B.i2c_got_reg) {
        B.i2c_reg_ptr = (uint8_t)v;
        B.i2c_got_reg = true;
    } else {
        if (B.i2c_reg_ptr < sizeof(B.imu_regs)) {
            B.imu_regs[B.i2c_reg_ptr++] = (uint8_t)v;
        }
    }
    B.i2c_idx++;
    B.i2c_isr = I2C_ISR_BUSY;
    if (B.i2c_idx >= B.i2c_nbytes) {
        B.i2c_pending_isr = B.i2c_autoend ? I2C_ISR_STOPF : (I2C_ISR_BUSY | I2C_ISR_TC);
    } else {
        B.i2c_pending_isr = I2C_ISR_BUSY | I2C_ISR_TXIS;
    }
    B.i2c_ready_cyc = active_cyc() + i2c_byte_cyc();
}

uint32_t sim_l432_i2c_rxdr_read(void) {
    advance_active_mcu(cpu_ticks(4ull));
    uint8_t b = (B.i2c_reg_ptr < sizeof(B.imu_regs)) ? B.imu_regs[B.i2c_reg_ptr++] : 0x00u;
    /* 读走 OUTZ_H_XL(0x2D) 后清 STATUS_REG 新数据位，模拟真实 BDU=1 行为 */
    if (B.i2c_reg_ptr > 0x2Du) B.imu_regs[0x1E] = 0x00u;
    B.i2c_idx++;
    B.i2c_isr = I2C_ISR_BUSY;
    if (B.i2c_idx >= B.i2c_nbytes) {
        B.i2c_pending_isr = B.i2c_autoend ? I2C_ISR_STOPF : (I2C_ISR_BUSY | I2C_ISR_TC);
        B.i2c_ready_cyc = active_cyc() + 3ull * SIM_TICKS_PER_US; /* STOP 条件 ~3 µs */
    } else {
        B.i2c_pending_isr = I2C_ISR_BUSY | I2C_ISR_RXNE;
        B.i2c_ready_cyc = active_cyc() + i2c_byte_cyc();
    }
    return b;
}

uint32_t sim_l432_i2c_isr_read(void) {
    advance_active_mcu(cpu_ticks(2ull));
    if (B.i2c_ready_cyc != 0 && active_cyc() >= B.i2c_ready_cyc) {
        B.i2c_isr = B.i2c_pending_isr;
        B.i2c_ready_cyc = 0;
    }
    return B.i2c_isr;
}

/* ==================== 7. nRF52840 寄存器与 S140 钩子实现 ==================== */
void sim_nrf_gpio_outset(int port_idx, uint32_t mask) {
    B.nrf_out[port_idx] |= mask;
    step_hardware_to(active_cyc());
}

void sim_nrf_gpio_outclr(int port_idx, uint32_t mask) {
    B.nrf_out[port_idx] &= ~mask;
    step_hardware_to(active_cyc());
}

void sim_nrf_gpio_cnf_write(int port_idx, int pin, uint32_t cnf) {
    /* P0.17 = OE_N 严禁设为推挽输出！ */
    if (port_idx == 0 && pin == 17 && (cnf & 1u) == GPIO_PIN_CNF_DIR_Output) {
        B.tel.hazard_mask |= HAZ_NRF_OE_N_DRIVEN_OUTPUT;
    }
}

uint32_t sim_nrf_gpio_in(int port_idx) {
    advance_active_mcu(cpu_ticks(4ull));
    uint64_t cyc = active_cyc();
    uint32_t in_v = B.nrf_out[port_idx];
    if (port_idx == 0) {
        int vbus = B.cfg.vbus_present ? 1 : 0;             /* P0.01 = VBUS_SENSE */
        int csn  = (g_sim_gpio[0].ODR >> 15) & 1u;         /* P0.11 = LINK_CS */
        int chrg = B.cfg.chrg_active ? 0 : 1;              /* P0.12 = CHRG_N (低有效) */
        int btn  = B.cfg.button_pressed ? 0 : 1;           /* P0.14 = BUTTON_N (低有效) */
        int oe_n = compute_oe_n(cyc) ? 1 : 0;              /* P0.17 = OE_N */
        in_v = (in_v & ~((1u << 1) | (1u << 11) | (1u << 12) | (1u << 14) | (1u << 17)))
             | ((uint32_t)vbus << 1)
             | ((uint32_t)csn  << 11)
             | ((uint32_t)chrg << 12)
             | ((uint32_t)btn  << 14)
             | ((uint32_t)oe_n << 17);
    }
    return in_v;
}

void sim_nrf_spis_task_acquire(void) {
    B.spis_released = false;
    g_sim_nrf_spis1.EVENTS_ACQUIRED = 1u;
}

void sim_nrf_spis_task_release(void) {
    B.spis_released = true;
    /* 检查 nRF 在检测到 VBUS 注入后何时把 req_mode 刷为 STOP(4) */
    const uint8_t *txp = (const uint8_t *)sim_resolve_nrf_ptr(g_sim_nrf_spis1.TXD.PTR);
    if (txp && g_sim_nrf_spis1.TXD.MAXCNT == 16u && B.tel.vbus_inject_us > 0 && B.tel.nrf_stop_us == 0) {
        if (txp[3] == 4u /* C08B_MODE_STOP */) {
            B.tel.nrf_stop_us = active_cyc() / SIM_TICKS_PER_US;
        }
    }
}

void sim_nrf_saadc_task_start(void) { g_sim_nrf_saadc.EVENTS_STARTED = 1u; }
void sim_nrf_saadc_task_stop(void)  { g_sim_nrf_saadc.EVENTS_STOPPED = 1u; }
void sim_nrf_saadc_task_sample(void) {
    advance_active_mcu(40ull * SIM_TICKS_PER_US); /* 40 µs TACQ */
    int16_t *dst = (int16_t *)sim_resolve_nrf_ptr(g_sim_nrf_saadc.RESULT.PTR);
    if (dst) {
        /* vbat = sample * 3600 * 2 / 4096 => sample = vbat * 4096 / 7200 */
        *dst = (int16_t)((B.cfg.vbat_mv * 4096u + 3600u) / 7200u);
    }
    g_sim_nrf_saadc.EVENTS_END = 1u;
}

void sim_nrf_uarte_task_starttx(void) {
    g_sim_nrf_uarte0.EVENTS_ENDTX = 1u;
}

void sim_nrf_clock_task_hfclkstart(void) {
    advance_active_mcu(300ull * SIM_TICKS_PER_US); /* 32 MHz HFXO 约 0.3 ms 起振 */
    g_sim_nrf_clock.EVENTS_HFCLKSTARTED = 1u;
}

void sim_nrf_timer2_task_clear(void) {
    B.timer2_clear_cyc = active_cyc();
}

void sim_nrf_timer2_task_capture(int idx) {
    advance_active_mcu(cpu_ticks(4ull));
    if (idx >= 0 && idx < 6) {
        g_sim_nrf_timer2.CC[idx] = (uint32_t)((active_cyc() - B.timer2_clear_cyc) / SIM_TICKS_PER_US);
    }
}

void sim_nrf_radio_task_txen(void) {
    advance_active_mcu(350ull * SIM_TICKS_PER_US); /* BLE 1M 31B 广播包空中耗时 ~350 µs */
    const uint8_t *pdu = (const uint8_t *)sim_resolve_nrf_ptr(g_sim_nrf_radio.PACKETPTR);
    if (pdu) {
        uint8_t total = (uint8_t)(2u + pdu[1]);
        if (total <= sizeof(B.tel.last_adv_pdu)) {
            std::memcpy(B.tel.last_adv_pdu, pdu, total);
            B.tel.last_adv_len = total;
            B.tel.radio_adv_count++;
        }
    }
    g_sim_nrf_radio.EVENTS_DISABLED = 1u;
}

void sim_nrf_system_reset(void) {
    B.tel.nrf_reset_count++;
    B.in_reset_jump = true;
    siglongjmp(B.nrf_reset_jmp, 1);
}

/* ==================== 8. S140 v7.3.0 BLE GATT SVC 实现 ==================== */
uint32_t sd_softdevice_enable(const nrf_clock_lf_cfg_t *p_clock_lf_cfg, nrf_fault_handler_t) {
    if (!p_clock_lf_cfg || p_clock_lf_cfg->source != NRF_CLOCK_LF_SRC_RC) {
        B.tel.hazard_mask |= HAZ_NRF_LFCLK_XTAL_ON_XL1;
    }
    g_sim_nrf_clock.EVENTS_HFCLKSTARTED = 1u;
    return NRF_SUCCESS;
}

uint32_t sd_ble_cfg_set(uint32_t, const ble_cfg_t *, uint32_t) { return NRF_SUCCESS; }
uint32_t sd_ble_enable(uint32_t *) { return NRF_SUCCESS; }

uint32_t sd_ble_gap_device_name_set(const ble_gap_conn_sec_mode_t *, const uint8_t *p_dev_name, uint16_t len) {
    size_t n = (len < sizeof(B.adv_dev_name) - 1) ? len : (sizeof(B.adv_dev_name) - 1);
    std::memcpy(B.adv_dev_name, p_dev_name, n);
    B.adv_dev_name[n] = '\0';
    return NRF_SUCCESS;
}

uint32_t sd_ble_uuid_vs_add(const ble_uuid128_t *p_vs_uuid, uint8_t *p_uuid_type) {
    uint8_t t = ++B.next_uuid_type;
    if (t < 16 && p_vs_uuid) B.uuid_type_to_suffix[t] = p_vs_uuid->uuid128[0];
    if (p_uuid_type) *p_uuid_type = t;
    return NRF_SUCCESS;
}

uint32_t sd_ble_gatts_service_add(uint8_t, const ble_uuid_t *, uint16_t *p_handle) {
    if (p_handle) *p_handle = ++B.next_attr_handle;
    return NRF_SUCCESS;
}

uint32_t sd_ble_gatts_characteristic_add(uint16_t, const ble_gatts_char_md_t *p_char_md,
                                         const ble_gatts_attr_t *p_attr_char_value, ble_gatts_char_handles_t *p_handles) {
    uint16_t vh = ++B.next_attr_handle;
    uint16_t ch = (p_char_md && p_char_md->char_props.notify) ? (++B.next_attr_handle) : 0u;
    if (p_handles) {
        p_handles->value_handle = vh;
        p_handles->cccd_handle  = ch;
    }
    if (p_attr_char_value && vh < 64) {
        B.attr_values[vh].assign(p_attr_char_value->p_value,
                                 p_attr_char_value->p_value + p_attr_char_value->init_len);
        uint8_t sfx = (p_attr_char_value->p_uuid && p_attr_char_value->p_uuid->type < 16)
                          ? B.uuid_type_to_suffix[p_attr_char_value->p_uuid->type]
                          : 0;
        if (sfx < 8) {
            B.char_val_handle[sfx]  = vh;
            B.char_cccd_handle[sfx] = ch;
        }
    }
    return NRF_SUCCESS;
}

uint32_t sd_ble_gatts_value_set(uint16_t, uint16_t handle, ble_gatts_value_t *p_value) {
    if (handle < 64 && p_value && p_value->p_value) {
        B.attr_values[handle].assign(p_value->p_value, p_value->p_value + p_value->len);
    }
    return NRF_SUCCESS;
}

uint32_t sd_ble_gap_adv_set_configure(uint8_t *p_adv_handle, const ble_gap_adv_data_t *p_adv_data, const ble_gap_adv_params_t *) {
    if (p_adv_handle) *p_adv_handle = 1u;
    if (p_adv_data && p_adv_data->scan_rsp_data.p_data && p_adv_data->scan_rsp_data.len >= 3) {
        const uint8_t *sr = p_adv_data->scan_rsp_data.p_data;
        if (sr[1] == BLE_GAP_AD_TYPE_COMPLETE_LOCAL_NAME) {
            size_t n = sr[0] - 1u;
            if (n >= sizeof(B.adv_dev_name)) n = sizeof(B.adv_dev_name) - 1;
            std::memcpy(B.adv_dev_name, sr + 2, n);
            B.adv_dev_name[n] = '\0';
        }
    }
    return NRF_SUCCESS;
}

uint32_t sd_ble_gap_adv_start(uint8_t, uint8_t) { return NRF_SUCCESS; }
uint32_t sd_ble_gap_phy_update(uint16_t, const ble_gap_phys_t *) { return NRF_SUCCESS; }
uint32_t sd_ble_gap_data_length_update(uint16_t, const void *, void *) { return NRF_SUCCESS; }
uint32_t sd_ble_gatts_sys_attr_set(uint16_t, const uint8_t *, uint16_t, uint32_t) { return NRF_SUCCESS; }

uint32_t sd_ble_gatts_exchange_mtu_reply(uint16_t, uint16_t server_rx_mtu) {
    B.ble_mtu = server_rx_mtu;
    return NRF_SUCCESS;
}

uint32_t sd_ble_evt_get(uint8_t *p_dest, uint16_t *p_len) {
    advance_active_mcu(8ull);
    if (B.ble_evt_q.empty()) return NRF_ERROR_NOT_FOUND;
    ble_evt_t ev = B.ble_evt_q.front();
    B.ble_evt_q.pop_front();
    if (p_dest && p_len && *p_len >= sizeof(ble_evt_t)) {
        std::memcpy(p_dest, &ev, sizeof(ble_evt_t));
        *p_len = sizeof(ble_evt_t);
    }
    return NRF_SUCCESS;
}

uint32_t sd_ble_gatts_hvx(uint16_t conn_handle, const ble_gatts_hvx_params_t *p_hvx) {
    if (!B.ble_connected || conn_handle != B.ble_conn_handle || !p_hvx || !p_hvx->p_data || !p_hvx->p_len) {
        return NRF_ERROR_RESOURCES;
    }
    uint8_t sfx = 0;
    for (uint8_t s = 2; s <= 6; s++) {
        if (B.char_val_handle[s] == p_hvx->handle) { sfx = s; break; }
    }
    uint16_t plen = *p_hvx->p_len;
    /* 统计 OE_N=1 期间是否漏发了 status!=0xC0 的全零坏帧 */
    if (sfx == 0x02u && plen >= 43u) {
        uint8_t ver = p_hvx->p_data[0];
        uint8_t cnt = p_hvx->p_data[2];
        size_t fsz = (ver == 4u) ? 54u : 27u;
        for (uint8_t i = 0; i < cnt; i++) {
            const uint8_t *fr = p_hvx->p_data + 16u + i * fsz;
            if ((fr[0] & 0xF0u) != 0xC0u || (ver == 4u && (fr[27] & 0xF0u) != 0xC0u)) {
                B.tel.zero_frames_leaked++;
            }
        }
    }
    B.ble_notify_q.push_back(BleNotifyItem{
        sfx,
        active_cyc() / SIM_TICKS_PER_US,
        std::vector<uint8_t>(p_hvx->p_data, p_hvx->p_data + plen),
    });
    return NRF_SUCCESS;
}

/* ==================== 9. 协程启动入口与 C ABI 导出 ==================== */
static void l432_fiber_trampoline() {
    fw_l432_main_entry();
    for (;;) sim_loop_poll();
}

static void nrf_fiber_trampoline() {
    if (sigsetjmp(B.nrf_reset_jmp, 1) != 0) {
        /* NVIC_SystemReset() 软复位：清零 nRF 固件 SRAM（保留 UICR 与 GPREGRET2），重新注册静态缓冲指针 */
        fw_restore_nrf_ram();
        B.nrf_ptrs.clear();
        fw_register_nrf_static_ptrs();
        B.spis_released = false;
        B.spis_in_xfer  = false;
        B.nrf_out[0] = B.nrf_out[1] = 0;
        std::memset(&g_sim_nrf_spis1, 0, sizeof(g_sim_nrf_spis1));
        std::memset(&g_sim_nrf_clock, 0, sizeof(g_sim_nrf_clock));
        std::memset(&g_sim_nrf_radio, 0, sizeof(g_sim_nrf_radio));
    }
    fw_nrf_main_entry();
    for (;;) sim_loop_poll();
}

static void setup_fiber(FiberCtx &ctx, uint8_t *stack_mem, size_t stack_sz, void (*fn)()) {
    std::memset(&ctx, 0, sizeof(ctx));
    uintptr_t sp = ((uintptr_t)(stack_mem + stack_sz)) & ~0xFULL;
    ctx.regs[10] = 0;
    ctx.regs[11] = (uintptr_t)fn;
    ctx.regs[12] = sp;
}

extern "C" {

void sim_default_config(SimConfig *cfg) {
    std::memset(cfg, 0, sizeof(*cfg));
    cfg->mainboard_rev    = SIM_MAINBOARD_MCU_U9_V001;
    cfg->subboard_kind    = SIM_SUBBOARD_AFE30P_16CH;
    cfg->vbus_present     = false;
    cfg->jp701_shorted    = false;
    cfg->force_oe_n_high  = false;
    cfg->avdd_3v0_ok      = true;
    cfg->imu_present      = true;
    cfg->wave_mode        = SIM_WAVE_SEMG_PHYSIOL;
    cfg->active_single_ch = 0;
    cfg->tone_amp_uv      = 250.0;
    cfg->mains_50hz_cm_uv = 400.0;
    cfg->crosstalk_ratio  = 1e-4; /* -80 dB */
    cfg->vbat_mv          = 3960u;
}

void sim_init(const SimConfig *cfg) {
    ensure_sig_handler();
    fw_restore_l432_ram();
    fw_restore_nrf_ram();

    B = BoardTwinState{};
    if (cfg) B.cfg = *cfg;
    else sim_default_config(&B.cfg);
    B.prng_state = 0xC08B20261115ULL;
    B.prev_link_cs = true;
    B.ble_conn_handle = BLE_CONN_HANDLE_INVALID;
    B.ble_mtu = 23u;

    /* 复位全部虚拟外设寄存器 */
    SystemCoreClock = 16000000u;
    nrf_SystemCoreClock = 64000000u;
    g_sim_dwt = DWT_Type{};
    g_sim_coredebug = CoreDebug_Type{};
    g_sim_flash = FLASH_TypeDef{};
    g_sim_pwr = PWR_TypeDef{PWR_CR1_VOS_0 << 1, 0u}; /* 上电默认 VOS Range 2 (0x400) 或复位值 */
    g_sim_rcc = RCC_TypeDef{};
    g_sim_rcc.CR.val = RCC_CR_HSIRDY;
    g_sim_rcc.CFGR.val = RCC_CFGR_SWS_HSI;
    for (int i = 0; i < 4; i++) {
        g_sim_gpio[i] = GPIO_TypeDef{};
        g_sim_gpio[i].MODER.port_idx = i;
        g_sim_gpio[i].PUPDR.port_idx = i;
        g_sim_gpio[i].IDR.port_idx   = i;
        g_sim_gpio[i].BSRR.port_idx  = i;
    }
    g_sim_spi1 = SPI_TypeDef{0, 0, {0, &g_sim_spi1}, 0};
    g_sim_spi3 = SPI_TypeDef{0, 0, {1, &g_sim_spi3}, 0};
    g_sim_i2c1 = I2C_TypeDef{};

    g_sim_nrf_p0 = NRF_GPIO_Type{};
    g_sim_nrf_p0.OUTSET.port_idx = 0; g_sim_nrf_p0.OUTCLR.port_idx = 0; g_sim_nrf_p0.IN.port_idx = 0;
    for (int p = 0; p < 32; p++) { g_sim_nrf_p0.PIN_CNF[p].port_idx = 0; g_sim_nrf_p0.PIN_CNF[p].pin = p; }
    g_sim_nrf_p1 = NRF_GPIO_Type{};
    g_sim_nrf_p1.OUTSET.port_idx = 1; g_sim_nrf_p1.OUTCLR.port_idx = 1; g_sim_nrf_p1.IN.port_idx = 1;
    for (int p = 0; p < 32; p++) { g_sim_nrf_p1.PIN_CNF[p].port_idx = 1; g_sim_nrf_p1.PIN_CNF[p].pin = p; }

    g_sim_nrf_uarte0 = NRF_UARTE_Type{};
    g_sim_nrf_saadc  = NRF_SAADC_Type{};
    g_sim_nrf_spis1  = NRF_SPIS_Type{};
    g_sim_nrf_radio  = NRF_RADIO_Type{};
    g_sim_nrf_ficr   = NRF_FICR_Type{{0x8B261115u, 0x0000C08Bu}};
    g_sim_nrf_uicr   = NRF_UICR_Type{0xFFFFFFFFu}; /* 新片出厂擦除态，验证 Errata 249 自动写 0x5A 并软复位一次 */
    g_sim_nrf_power  = NRF_POWER_Type{0u};
    g_sim_nrf_nvmc   = NRF_NVMC_Type{0u, 1u};
    g_sim_nrf_clock  = NRF_CLOCK_Type{};
    g_sim_nrf_timer2 = NRF_TIMER_Type{};
    for (int i = 0; i < 6; i++) g_sim_nrf_timer2.TASKS_CAPTURE[i].idx = i;

    /* LSM6DS3TR-C 初始 WHO_AM_I = 0x6A */
    B.imu_regs[0x0F] = 0x6Au;

    /* 配置 AFE 芯片存在性与 ID */
    if (B.cfg.subboard_kind == SIM_SUBBOARD_AFE30P_16CH) {
        B.chips[0].present = true; B.chips[0].is_1292 = false;
        B.chips[0].id_byte = B.cfg.id_a_override ? B.cfg.id_a_override : 0x92u;
        B.chips[1].present = true; B.chips[1].is_1292 = false;
        B.chips[1].id_byte = B.cfg.id_b_override ? B.cfg.id_b_override : 0x92u;
    } else if (B.cfg.subboard_kind == SIM_SUBBOARD_D20_8CH) {
        B.chips[0].present = true; B.chips[0].is_1292 = false;
        B.chips[0].id_byte = B.cfg.id_a_override ? B.cfg.id_a_override : 0x92u;
        B.chips[1].present = false;
    } else if (B.cfg.subboard_kind == SIM_SUBBOARD_ADS1292_2CH) {
        B.chips[0].present = true; B.chips[0].is_1292 = true;
        B.chips[0].id_byte = B.cfg.id_a_override ? B.cfg.id_a_override : 0x53u;
        B.chips[1].present = false;
        /* 若测 PA4 开路假阳性反例，预充 3.3V 寄生残荷检验固件 10us P_DOWN 泄放是否生效 */
        B.pa4_cap_v = B.cfg.avdd_3v0_ok ? 3.0 : 3.3;
    } else if (B.cfg.subboard_kind == SIM_SUBBOARD_GARBLED_B) {
        B.chips[0].present = true; B.chips[0].is_1292 = false; B.chips[0].id_byte = 0x92u;
        B.chips[1].present = true; B.chips[1].is_1292 = false; B.chips[1].id_byte = 0x80u;
    }
    for (int i = 0; i < 2; i++) {
        if (B.chips[i].present) reset_ads_chip_regs(B.chips[i], i);
    }

    fw_register_nrf_static_ptrs();
    setup_fiber(B.ctx_l432, g_l432_stack, sizeof(g_l432_stack), l432_fiber_trampoline);
    setup_fiber(B.ctx_nrf,  g_nrf_stack,  sizeof(g_nrf_stack),  nrf_fiber_trampoline);
}

void sim_step_us(uint64_t delta_us) {
    uint64_t base = (B.cyc_l432 < B.cyc_nrf) ? B.cyc_l432 : B.cyc_nrf;
    B.target_cyc = base + delta_us * SIM_TICKS_PER_US;
    while (B.cyc_l432 < B.target_cyc || B.cyc_nrf < B.target_cyc) {
        if (B.cyc_l432 <= B.cyc_nrf) {
            B.active_mcu = MCU_L432;
            sim_fiber_switch(&B.ctx_host, &B.ctx_l432);
        } else {
            B.active_mcu = MCU_NRF;
            sim_fiber_switch(&B.ctx_host, &B.ctx_nrf);
        }
    }
    B.active_mcu = MCU_HOST;
    step_hardware_to(B.target_cyc);
}

void sim_set_vbus(bool vbus_present) {
    if (vbus_present && !B.cfg.vbus_present) {
        B.tel.vbus_inject_us = ((B.cyc_l432 < B.cyc_nrf) ? B.cyc_l432 : B.cyc_nrf) / SIM_TICKS_PER_US;
    }
    B.cfg.vbus_present = vbus_present;
}

void sim_set_force_oe_n_high(bool force_high) {
    if (force_high && !B.cfg.force_oe_n_high) {
        B.tel.vbus_inject_us = ((B.cyc_l432 < B.cyc_nrf) ? B.cyc_l432 : B.cyc_nrf) / SIM_TICKS_PER_US;
    }
    B.cfg.force_oe_n_high = force_high;
}

void sim_set_avdd_3v0(bool ok) {
    B.cfg.avdd_3v0_ok = ok;
    if (!ok) B.pa4_cap_v = 0.0;
}

void sim_set_button(bool pressed) {
    B.cfg.button_pressed = pressed;
}

void sim_set_readback_fault(bool enable) {
    B.cfg.reg_readback_fault = enable;
}

void sim_get_telemetry(SimTelemetry *out) {
    if (!out) return;
    fw_copy_rtt_logs(B.tel.l432_rtt, B.tel.nrf_rtt);
    *out = B.tel;
}

/* ---------- BLE GATT 主机驱动接口 ---------- */
void sim_ble_connect(uint16_t mtu) {
    B.ble_connected = true;
    B.ble_conn_handle = 1u;
    ble_evt_t ev{};
    ev.header.evt_id = BLE_GAP_EVT_CONNECTED;
    ev.evt.gap_evt.conn_handle = 1u;
    B.ble_evt_q.push_back(ev);

    ble_evt_t mev{};
    mev.header.evt_id = BLE_GATTS_EVT_EXCHANGE_MTU_REQUEST;
    mev.evt.gatts_evt.conn_handle = 1u;
    mev.evt.gatts_evt.params.exchange_mtu_request.client_rx_mtu = mtu;
    B.ble_evt_q.push_back(mev);
    sim_step_us(500);
}

void sim_ble_disconnect(void) {
    if (!B.ble_connected) return;
    B.ble_connected = false;
    B.ble_conn_handle = BLE_CONN_HANDLE_INVALID;
    ble_evt_t ev{};
    ev.header.evt_id = BLE_GAP_EVT_DISCONNECTED;
    ev.evt.gap_evt.conn_handle = 1u;
    B.ble_evt_q.push_back(ev);
    sim_step_us(500);
}

int sim_ble_subscribe(uint8_t char_suffix, bool enable) {
    if (char_suffix >= 8 || B.char_cccd_handle[char_suffix] == 0) return -1;
    ble_evt_t ev{};
    ev.header.evt_id = BLE_GATTS_EVT_WRITE;
    ev.evt.gatts_evt.conn_handle = B.ble_conn_handle;
    ev.evt.gatts_evt.params.write.handle = B.char_cccd_handle[char_suffix];
    ev.evt.gatts_evt.params.write.len = 2u;
    ev.evt.gatts_evt.params.write.data[0] = enable ? 1u : 0u;
    ev.evt.gatts_evt.params.write.data[1] = 0u;
    B.ble_evt_q.push_back(ev);
    sim_step_us(500);
    return 0;
}

int sim_ble_write_ctrl(const uint8_t *data, uint16_t len) {
    if (B.char_val_handle[0x05] == 0 || len > 32) return -1;
    ble_evt_t ev{};
    ev.header.evt_id = BLE_GATTS_EVT_WRITE;
    ev.evt.gatts_evt.conn_handle = B.ble_conn_handle;
    ev.evt.gatts_evt.params.write.handle = B.char_val_handle[0x05];
    ev.evt.gatts_evt.params.write.len = len;
    std::memcpy(ev.evt.gatts_evt.params.write.data, data, len);
    B.ble_evt_q.push_back(ev);
    sim_step_us(500);
    return 0;
}

int sim_ble_read_char(uint8_t char_suffix, uint8_t *out_buf, int max_len) {
    /* 推进 250 µs 确保 nRF 刷新最新 STATUS / META */
    sim_step_us(250);
    if (char_suffix >= 8) return -1;
    uint16_t vh = B.char_val_handle[char_suffix];
    if (vh == 0 || vh >= 64) return -1;
    const auto &vec = B.attr_values[vh];
    int n = ((int)vec.size() < max_len) ? (int)vec.size() : max_len;
    if (out_buf && n > 0) std::memcpy(out_buf, vec.data(), (size_t)n);
    return n;
}

int sim_ble_pop_notify(uint8_t *out_char_suffix, uint8_t *out_pkt, int max_len, uint64_t *out_ts_us) {
    if (B.ble_notify_q.empty()) return 0;
    BleNotifyItem item = std::move(B.ble_notify_q.front());
    B.ble_notify_q.pop_front();
    if (out_char_suffix) *out_char_suffix = item.char_suffix;
    if (out_ts_us) *out_ts_us = item.ts_us;
    int n = ((int)item.payload.size() < max_len) ? (int)item.payload.size() : max_len;
    if (out_pkt && n > 0) std::memcpy(out_pkt, item.payload.data(), (size_t)n);
    return n;
}

int sim_ble_get_adv_name(char *out_name, int max_len) {
    int n = (int)std::strlen(B.adv_dev_name);
    if (n >= max_len) n = max_len - 1;
    if (out_name && n >= 0) {
        std::memcpy(out_name, B.adv_dev_name, (size_t)n);
        out_name[n] = '\0';
    }
    return n;
}

} // extern "C"
