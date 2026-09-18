package com.fraud.detection.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.*;

import java.math.BigDecimal;
import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
@JsonIgnoreProperties(ignoreUnknown = true)
public class MlScoreResponse {

    @JsonProperty("transaction_ref")
    private String transactionRef;

    @JsonProperty("fraud_probability")
    private BigDecimal fraudProbability;

    @JsonProperty("risk_level")
    private String riskLevel;

    @JsonProperty("recommendation")
    private String recommendation;

    @JsonProperty("model_version")
    private String modelVersion;

    @JsonProperty("risk_factors")
    private List<RiskFactorDto> riskFactors;

    @JsonProperty("evaluated_at")
    private String evaluatedAt;

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class RiskFactorDto {
        private String feature;
        private Double contribution;
        private String description;
    }
}
