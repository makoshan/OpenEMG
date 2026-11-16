#pragma once
#include <limits.h>
#include <stdint.h>
#include "../hw_twin/v001_board.hpp"

extern uint32_t SystemCoreClock;
void SystemCoreClockUpdate(void);
uint32_t SysTick_Config(uint32_t ticks);

/* ---------- DWT & CoreDebug ---------- */
struct SimDwtCyccntReg {
    operator uint32_t() const volatile { return sim_l432_dwt_read(); }
    uint32_t operator=(uint32_t v) volatile { sim_l432_dwt_write(v); return v; }
};

typedef struct {
    volatile uint32_t CTRL;
    SimDwtCyccntReg   CYCCNT;
} DWT_Type;

typedef struct {
    volatile uint32_t DEMCR;
} CoreDebug_Type;

#define DWT_CTRL_CYCCNTENA_Msk      (1u << 0)
#define CoreDebug_DEMCR_TRCENA_Msk  (1u << 24)

extern DWT_Type       g_sim_dwt;
extern CoreDebug_Type g_sim_coredebug;
#define DWT       (&g_sim_dwt)
#define CoreDebug (&g_sim_coredebug)

/* ---------- FLASH & PWR ---------- */
typedef struct {
    volatile uint32_t ACR;
} FLASH_TypeDef;

#define FLASH_ACR_LATENCY       (7u << 0)
#define FLASH_ACR_LATENCY_3WS   (3u << 0)
#define FLASH_ACR_PRFTEN        (1u << 8)
#define FLASH_ACR_ICEN          (1u << 9)
#define FLASH_ACR_DCEN          (1u << 10)

extern FLASH_TypeDef g_sim_flash;
#define FLASH (&g_sim_flash)

typedef struct {
    volatile uint32_t CR1;
    volatile uint32_t SR2;
} PWR_TypeDef;

#define PWR_CR1_VOS_Pos         9u
#define PWR_CR1_VOS             (3u << PWR_CR1_VOS_Pos)
#define PWR_CR1_VOS_0           (1u << PWR_CR1_VOS_Pos)
#define PWR_SR2_VOSF            (1u << 10)

extern PWR_TypeDef g_sim_pwr;
#define PWR (&g_sim_pwr)

/* ---------- RCC ---------- */
struct SimRccCrReg {
    uint32_t val;
    operator uint32_t() const volatile { return val; }
    uint32_t operator=(uint32_t v) volatile { val = sim_l432_rcc_cr_write(v); return val; }
    uint32_t operator|=(uint32_t m) volatile { val = sim_l432_rcc_cr_write(val | m); return val; }
    uint32_t operator&=(uint32_t m) volatile { val = sim_l432_rcc_cr_write(val & m); return val; }
};

struct SimRccCfgrReg {
    uint32_t val;
    operator uint32_t() const volatile { return val; }
    uint32_t operator=(uint32_t v) volatile { val = sim_l432_rcc_cfgr_write(v); return val; }
};

typedef struct {
    SimRccCrReg       CR;
    SimRccCfgrReg     CFGR;
    volatile uint32_t PLLCFGR;
    volatile uint32_t AHB2ENR;
    volatile uint32_t APB2ENR;
    volatile uint32_t APB1ENR1;
} RCC_TypeDef;

#define RCC_CR_HSION                (1u << 8)
#define RCC_CR_HSIRDY               (1u << 10)
#define RCC_CR_PLLON                (1u << 24)
#define RCC_CR_PLLRDY               (1u << 25)
#define RCC_CFGR_SW                 (3u << 0)
#define RCC_CFGR_SW_HSI             (1u << 0)
#define RCC_CFGR_SW_PLL             (3u << 0)
#define RCC_CFGR_SWS                (3u << 2)
#define RCC_CFGR_SWS_HSI            (1u << 2)
#define RCC_CFGR_SWS_PLL            (3u << 2)
#define RCC_CFGR_PPRE1_Pos          8u
#define RCC_CFGR_PPRE1_Msk          (7u << RCC_CFGR_PPRE1_Pos)
#define RCC_CFGR_PPRE1_DIV4         (5u << RCC_CFGR_PPRE1_Pos)
#define RCC_CFGR_PPRE2_Pos          11u
#define RCC_CFGR_PPRE2_Msk          (7u << RCC_CFGR_PPRE2_Pos)
#define RCC_CFGR_PPRE2_DIV4         (5u << RCC_CFGR_PPRE2_Pos)
#define RCC_PLLCFGR_PLLSRC          (3u << 0)
#define RCC_PLLCFGR_PLLSRC_HSI      (2u << 0)
#define RCC_PLLCFGR_PLLM_Pos        4u
#define RCC_PLLCFGR_PLLM            (7u << RCC_PLLCFGR_PLLM_Pos)
#define RCC_PLLCFGR_PLLN_Pos        8u
#define RCC_PLLCFGR_PLLN            (0x7Fu << RCC_PLLCFGR_PLLN_Pos)
#define RCC_PLLCFGR_PLLREN          (1u << 24)
#define RCC_PLLCFGR_PLLR_Pos        25u
#define RCC_PLLCFGR_PLLR            (3u << RCC_PLLCFGR_PLLR_Pos)
#define RCC_AHB2ENR_GPIOAEN         (1u << 0)
#define RCC_AHB2ENR_GPIOBEN         (1u << 1)
#define RCC_AHB2ENR_GPIOCEN         (1u << 2)
#define RCC_AHB2ENR_GPIOHEN         (1u << 7)
#define RCC_APB2ENR_SPI1EN          (1u << 12)
#define RCC_APB1ENR1_SPI3EN         (1u << 15)
#define RCC_APB1ENR1_I2C1EN         (1u << 21)
#define RCC_APB1ENR1_PWREN          (1u << 28)

extern RCC_TypeDef g_sim_rcc;
#define RCC (&g_sim_rcc)

/* ---------- GPIO ---------- */
struct SimGpioBsrrReg {
    int port_idx;
    uint32_t operator=(uint32_t v) volatile {
        sim_l432_gpio_bsrr(port_idx, v);
        return v;
    }
};

struct SimGpioIdrReg {
    int port_idx;
    operator uint32_t() const volatile {
        return sim_l432_gpio_idr(port_idx);
    }
};

struct SimGpioCfgReg {
    int port_idx;
    uint32_t val;
    operator uint32_t() const volatile { return val; }
    uint32_t operator=(uint32_t v) volatile {
        val = v;
        sim_l432_gpio_cfg_changed(port_idx);
        return v;
    }
};

typedef struct {
    SimGpioCfgReg     MODER;
    volatile uint32_t OTYPER;
    volatile uint32_t OSPEEDR;
    SimGpioCfgReg     PUPDR;
    SimGpioIdrReg     IDR;
    volatile uint32_t ODR;
    SimGpioBsrrReg    BSRR;
    uint32_t          AFR[2];
} GPIO_TypeDef;

extern GPIO_TypeDef g_sim_gpio[4];
#define GPIOA (&g_sim_gpio[0])
#define GPIOB (&g_sim_gpio[1])
#define GPIOC (&g_sim_gpio[2])
#define GPIOH (&g_sim_gpio[3])

/* ---------- SPI ---------- */
struct SPI_TypeDef;
struct SimSpiSrReg {
    int spi_idx;
    SPI_TypeDef *parent;
    operator uint32_t() const volatile;
};

struct SPI_TypeDef {
    volatile uint32_t CR1;
    volatile uint32_t CR2;
    SimSpiSrReg       SR;
    volatile uint32_t DR;
};

inline SimSpiSrReg::operator uint32_t() const volatile {
    return sim_l432_spi_sr_read(spi_idx, &parent->DR, parent->CR1);
}

#define SPI_CR1_CPHA    (1u << 0)
#define SPI_CR1_MSTR    (1u << 2)
#define SPI_CR1_BR_Pos  3u
#define SPI_CR1_SPE     (1u << 6)
#define SPI_CR1_SSI     (1u << 8)
#define SPI_CR1_SSM     (1u << 9)
#define SPI_CR2_DS_Pos  8u
#define SPI_CR2_FRXTH   (1u << 12)
#define SPI_SR_RXNE     (1u << 0)
#define SPI_SR_TXE      (1u << 1)

extern SPI_TypeDef g_sim_spi1;
extern SPI_TypeDef g_sim_spi3;
#define SPI1 (&g_sim_spi1)
#define SPI3 (&g_sim_spi3)

/* ---------- I2C ---------- */
struct SimI2cCr1Reg {
    uint32_t val;
    operator uint32_t() const volatile { return val; }
    uint32_t operator=(uint32_t v) volatile { val = v; sim_l432_i2c_cr1_write(v); return v; }
};
struct SimI2cCr2Reg {
    uint32_t val;
    operator uint32_t() const volatile { return val; }
    uint32_t operator=(uint32_t v) volatile { val = v; sim_l432_i2c_cr2_write(v); return v; }
};
struct SimI2cTxdrReg {
    uint32_t operator=(uint32_t v) volatile { sim_l432_i2c_txdr_write(v); return v; }
};
struct SimI2cRxdrReg {
    operator uint32_t() const volatile { return sim_l432_i2c_rxdr_read(); }
};
struct SimI2cIsrReg {
    operator uint32_t() const volatile { return sim_l432_i2c_isr_read(); }
};
struct SimI2cIcrReg {
    uint32_t operator=(uint32_t v) volatile { sim_l432_i2c_icr_write(v); return v; }
};

typedef struct {
    SimI2cCr1Reg      CR1;
    SimI2cCr2Reg      CR2;
    volatile uint32_t TIMINGR;
    SimI2cIsrReg      ISR;
    SimI2cIcrReg      ICR;
    SimI2cRxdrReg     RXDR;
    SimI2cTxdrReg     TXDR;
} I2C_TypeDef;

#define I2C_CR1_PE          (1u << 0)
#define I2C_CR2_RD_WRN      (1u << 10)
#define I2C_CR2_START       (1u << 13)
#define I2C_CR2_NBYTES_Pos  16u
#define I2C_CR2_AUTOEND     (1u << 25)
#define I2C_ISR_TXIS        (1u << 1)
#define I2C_ISR_RXNE        (1u << 2)
#define I2C_ISR_NACKF       (1u << 4)
#define I2C_ISR_STOPF       (1u << 5)
#define I2C_ISR_TC          (1u << 6)
#define I2C_ISR_BUSY        (1u << 15)
#define I2C_ICR_NACKCF      (1u << 4)
#define I2C_ICR_STOPCF      (1u << 5)

extern I2C_TypeDef g_sim_i2c1;
#define I2C1 (&g_sim_i2c1)
