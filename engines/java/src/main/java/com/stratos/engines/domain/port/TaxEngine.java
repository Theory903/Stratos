package com.stratos.engines.domain.port;

import java.math.BigDecimal;
import java.util.Map;

/**
 * Tax engine port — Interface Segregation: narrow tax-only contract.
 * Implementing adapters provide the concrete tax logic.
 */
public interface TaxEngine {
    BigDecimal computeOptimalTaxLiability(Map<String, BigDecimal> income, String jurisdiction);

    Map<String, BigDecimal> simulateCapitalGains(Map<String, BigDecimal> positions, int holdingPeriodDays);
}
