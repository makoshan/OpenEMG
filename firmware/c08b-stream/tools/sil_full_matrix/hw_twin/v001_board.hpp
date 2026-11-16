#pragma once
#include <cstddef>
#include <cstdint>

/* ============================================================================
 * OpenEMG v0.01 (MCU-U9 Rev0.01 + AFE-30P / D20-8CH / ADS1292-2ch-R9)
 * 寄存器与网表级双核虚拟硬件孪生引擎 (Silicon-in-the-Loop Hardware Twin)
 * ============================================================================ */

enum SimMainboardRev : int {
    SIM_MAINBOARD_MCU_U9_V001 = 0, /* Y41: PH3=L_BOOT0(R5 下拉=0)，VBUS 仅进 nRF P0.01，Q3/U4/U16/U19+R701/R702 互锁 */
    SIM_MAINBOARD_R4U6        = 1, /* 旧版对照: PH3 并入 VBUS_SENSE */
};

enum SimSubBoardKind : int {
    SIM_SUBBOARD_NONE        = 0,  /* 未插采集板 */
    SIM_SUBBOARD_AFE30P_16CH = 16, /* Y42: OpenEMG v0.01 AFE-30P 双 ADS1298 (Pin62=+2.5V, Pin60=AGND, 17/18 独立悬空) */
    SIM_SUBBOARD_D20_8CH     = 8,  /* D20-8CH 单面 ADS1298 (U1=0x92, U2 未贴) */
    SIM_SUBBOARD_ADS1292_2CH = 2,  /* ADS1292-2ch-R9 六触点 (U1=0x53, J2.7=NC, J2.6=PWDN/RESET, PA4=AVDD_SENSE) */
    SIM_SUBBOARD_GARBLED_B   = 99, /* 故障注入：U1=0x92, U2=0x80 半死乱码 */
};

enum SimWaveMode : int {
    SIM_WAVE_SEMG_PHYSIOL = 0, /* 生理肌电脉冲 + 50Hz 工频共模 + 16x16 邻道串扰 (-80 dB) */
    SIM_WAVE_TONE_SWEEP   = 1, /* 多频正弦频响测试 (各通道固定精确频率与幅度) */
    SIM_WAVE_SINGLE_CH    = 2, /* 单通道激励串扰矩阵测定 (仅 active_single_ch 注入正弦，测其余 15 路串扰) */
};

enum SimHazardBits : uint32_t {
    HAZ_NONE                     = 0,
    HAZ_RLDREF_INT_SHORT_AGND    = 1u << 0, /* Pin 60=AGND 却置 CONFIG3.RLDREF_INT(0x08) 顶牛短路 */
    HAZ_PIN62_AVDD_RLD_MEAS      = 1u << 1, /* v0.01 Pin 62=+2.5V 却置 CONFIG3.RLD_MEAS(0x10) 或 MUX=0x02 */
    HAZ_VREF_4V_ON_2V5_RAIL      = 1u << 2, /* ±2.5V 模拟轨下误开 4.0V 基准 CONFIG3.VREF_4V(0x20) */
    HAZ_GPIO_OUTPUT_SHORT_GND    = 1u << 3, /* GPIO1/2/4 接地却配成推挽输出 */
    HAZ_RLD_NO_WARMUP_OR_U2_RLD  = 1u << 4, /* 未等 150ms VREF 建立即合上 PD_RLD，或对 U2 开 RLD */
    HAZ_ADS1292_SPI_TSDECODE     = 1u << 5, /* ADS1292 SCLK > 20MHz 或命令字节间隔 < 4*tCLK(7.81us) */
    HAZ_ADS1292_VCAP1_UNDERTIME  = 1u << 6, /* ADS1292 未等满 512ms tPOR / 1000ms VCAP1 或 PWDN 低脉冲 >=4000us */
    HAZ_NRF_LFCLK_XTAL_ON_XL1    = 1u << 7, /* nRF 误开外部 XTAL 劫持 P0.00/XL1 (BENCH_EN) 旁路互锁 */
    HAZ_NRF_OE_N_DRIVEN_OUTPUT   = 1u << 8, /* nRF P0.17(OE_N) 被误设为输出 */
    HAZ_SPI3_OVER_8MHZ           = 1u << 9, /* L432 SPI3 SCLK > 8 MHz 违反 nRF52840 SPIS1 物理上限 */
    HAZ_L432_PLL_FLASH_WS        = 1u << 10,/* L432 切换 64MHz PLL 前未设 VOS Range1 或 Flash < 3WS */
    HAZ_ADS1298_CLK_EN_PIN37     = 1u << 11,/* ADS1298 CONFIG1.CLK_EN(0x20)=1 与外部 2.048MHz 晶振 X1 脚 37 冲突 */
};

struct SimConfig {
    int      mainboard_rev;
    int      subboard_kind;
    uint8_t  id_a_override;       /* 0 = 按板型默认 (0x92 / 0x53) */
    uint8_t  id_b_override;       /* 0 = 按板型默认 (0x92 / 0x00) */
    bool     vbus_present;        /* USB VBUS 5V 状态 */
    bool     jp701_shorted;       /* 台架 JP701 短接解互锁 */
    bool     force_oe_n_high;     /* 硬件故障注入：强制拉高 OE_N=1（U16/U19 三态，R701/R702 下拉 PA2/PA6=0） */
    bool     avdd_3v0_ok;         /* 2CH U3 3.0V LDO 是否正常输出 */
    bool     strict_ads1292_por;  /* 严格执行 TI SBAS502C 冷启动 tPOR=2^18*tCLK=512ms 期间 SPI 静默锁死 */
    bool     force_short_bringup_por; /* 必挂反例 NC-1f：模拟旧版 <512ms POR（将 tPOR 门限设为 1500ms 验证拦截器） */
    bool     imu_present;         /* LSM6DS3TR-C @ 0x6A 是否在位 */
    bool     imu_bus_stuck_low;   /* 故障注入：I2C1 SCL/SDA 被拉低 */
    bool     drdy_a_timeout;      /* 故障注入：DRDY_A 停振不拉低 */
    bool     drdy_b_stuck_low;    /* 故障注入：16CH DRDY_B 卡低不被共享 SCLK 清除 */
    bool     reg_readback_fault;  /* 故障注入：ADS 寄存器回读篡改 1 位 */
    bool     corrupt_spi3_crc;    /* 故障注入：翻转 SPI3 MOSI 1 bit 破坏 CRC */
    bool     old_u2_cfg2_zero_bug;/* 回归反例 NC-1a：模拟旧版固件强制把 U2 CONFIG2 写成 0x00 */
    uint32_t inject_hazard_cfg3;  /* 安全门反例 NC-1b：向 ADS1298 CONFIG3 额外或入危险位 */
    uint32_t inject_hazard_gpio;  /* 安全门反例 NC-1b：覆盖 ADS1298 GPIO 寄存器 */
    uint32_t inject_periodic_stall_us; /* 反例 NC-2h：采集中周期性注入 CPU 中断停顿 (µs)，检验 DRDY 漏采记账 */
    int      wave_mode;           /* SimWaveMode */
    int      active_single_ch;    /* SIM_WAVE_SINGLE_CH 激励通道 0..15 */
    double   tone_amp_uv;         /* 注入正弦峰值 µV */
    double   mains_50hz_cm_uv;    /* 50 Hz 工频共模干扰峰值 µV（RLD 闭环抑制 26 dB） */
    double   crosstalk_ratio;     /* 邻道电容串扰系数（默认 1e-4 = -80 dB） */
    uint32_t vbat_mv;             /* 电池电压 mV（默认 3960 mV） */
    bool     chrg_active;         /* TP4054 CHRG_N 低有效充电状态 */
    bool     button_pressed;      /* SW300 BUTTON_N 低有效按键状态 */
};

struct SimTelemetry {
    uint64_t sim_time_us;
    uint32_t hazard_mask;
    uint32_t l432_hclk_hz;
    uint32_t nrf_reset_count;
    uint32_t approtect_disable_reg;
    uint32_t spi1_sclk_hz;
    uint32_t spi3_sclk_hz;
    uint32_t spi3_frames_sent;
    uint32_t spi3_crc_ok_count;
    uint32_t spi3_crc_fail_count;
    uint32_t radio_adv_count;
    uint8_t  last_adv_pdu[39];
    uint8_t  last_adv_len;
    uint8_t  last_report_97b[97];
    bool     has_report_97b;
    uint8_t  ads_regs[2][0x1A];
    bool     ana_en_level;
    bool     oe_n_level;
    bool     ads_pwdn_level;
    bool     ads_reset_level;
    bool     ads_start_level;
    bool     pwr_hold_level;
    bool     led_pin_level;
    uint64_t vbus_inject_us;
    uint64_t ana_en_off_us;       /* 注入 VBUS/互锁后 L432 切断 ANA_EN 的精确微秒时刻 */
    uint64_t nrf_stop_us;         /* 注入 VBUS 后 nRF 置 STOP/INTERLOCK 的精确微秒时刻 */
    uint32_t zero_frames_leaked;  /* OE_N=1 期间漏进 BLE HVX 通知的 status!=0xC0 坏样本数 */
    char     l432_rtt[2048];
    char     nrf_rtt[2048];
};

/* 供 mock_inc 头调用的底层寄存器钩子 */
void     sim_loop_poll(void);
uint32_t sim_l432_rcc_cr_write(uint32_t v);
uint32_t sim_l432_rcc_cfgr_write(uint32_t v);
uint32_t sim_l432_dwt_read(void);
void     sim_l432_dwt_write(uint32_t v);
void     sim_l432_gpio_bsrr(int port_idx, uint32_t v);
uint32_t sim_l432_gpio_idr(int port_idx);
void     sim_l432_gpio_cfg_changed(int port_idx);
uint32_t sim_l432_spi_sr_read(int spi_idx, volatile uint32_t *dr_mem, uint32_t cr1);
void     sim_l432_i2c_cr2_write(uint32_t v);
void     sim_l432_i2c_txdr_write(uint32_t v);
uint32_t sim_l432_i2c_rxdr_read(void);
uint32_t sim_l432_i2c_isr_read(void);
void     sim_l432_i2c_icr_write(uint32_t v);
void     sim_l432_i2c_cr1_write(uint32_t v);

void     sim_nrf_gpio_outset(int port_idx, uint32_t mask);
void     sim_nrf_gpio_outclr(int port_idx, uint32_t mask);
uint32_t sim_nrf_gpio_in(int port_idx);
void     sim_nrf_gpio_cnf_write(int port_idx, int pin, uint32_t cnf);
void     sim_nrf_spis_task_acquire(void);
void     sim_nrf_spis_task_release(void);
void     sim_nrf_saadc_task_start(void);
void     sim_nrf_saadc_task_sample(void);
void     sim_nrf_saadc_task_stop(void);
void     sim_nrf_uarte_task_starttx(void);
void     sim_nrf_clock_task_hfclkstart(void);
void     sim_nrf_timer2_task_capture(int idx);
void     sim_nrf_timer2_task_clear(void);
void     sim_nrf_radio_task_txen(void);
void     sim_nrf_system_reset(void);

/* 指针注册表：安全还原 64 位宿主上被固件强转为 uint32_t 的静态缓冲地址 */
void     sim_register_nrf_ptr(const volatile void *p, size_t size);
void    *sim_resolve_nrf_ptr(uint32_t ptr32);

/* C ABI 导出（供 Python ctypes 直接驱动） */
extern "C" {
void     sim_default_config(SimConfig *cfg);
void     sim_init(const SimConfig *cfg);
void     sim_step_us(uint64_t delta_us);
void     sim_set_vbus(bool vbus_present);
void     sim_set_force_oe_n_high(bool force_high);
void     sim_set_avdd_3v0(bool ok);
void     sim_set_button(bool pressed);
void     sim_set_readback_fault(bool enable);
void     sim_set_corrupt_spi3_crc(bool enable);
void     sim_get_telemetry(SimTelemetry *out);

/* S140 BLE GATT 主机客户端接口（供 Python 适配 host/c08b_stream.py BleakClient 接口） */
void     sim_ble_connect(uint16_t mtu);
void     sim_ble_disconnect(void);
int      sim_ble_subscribe(uint8_t char_suffix, bool enable);
int      sim_ble_write_ctrl(const uint8_t *data, uint16_t len);
int      sim_ble_read_char(uint8_t char_suffix, uint8_t *out_buf, int max_len);
int      sim_ble_pop_notify(uint8_t *out_char_suffix, uint8_t *out_pkt, int max_len, uint64_t *out_ts_us);
int      sim_ble_get_adv_name(char *out_name, int max_len);
}
