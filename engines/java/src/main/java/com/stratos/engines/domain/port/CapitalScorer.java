package com.stratos.engines.domain.port;

import java.math.BigDecimal;

/**
 * Capital scoring port — narrow interface for capital efficiency.
 */
public interface CapitalScorer {
    BigDecimal computeROIC(String ticker);

    BigDecimal computeCapitalEfficiency(String ticker);
}
