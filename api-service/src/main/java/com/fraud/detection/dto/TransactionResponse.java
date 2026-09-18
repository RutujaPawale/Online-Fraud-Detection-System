package com.fraud.detection.dto;

import com.fraud.detection.entity.DecisionStatus;
import com.fraud.detection.entity.ReviewStatus;
import lombok.*;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class TransactionResponse {

    private UUID id;
    private String transactionRef;
    private String userId;
    private BigDecimal amount;
    private String currency;
    private String productCd;
    private String card4;
    private String card6;
    @com.fasterxml.jackson.annotation.JsonProperty("pEmailDomain")
    private String pEmailDomain;

    @com.fasterxml.jackson.annotation.JsonProperty("rEmailDomain")
    private String rEmailDomain;
    private String deviceType;
    private String deviceInfo;
    private DecisionStatus status;
    private Instant createdAt;

    // Fraud Assessment details
    private BigDecimal fraudProbability;
    private String riskLevel;
    private String modelVersion;
    private String riskFactorsJson;

    // Review Case details (if flagged)
    private UUID reviewCaseId;
    private ReviewStatus reviewStatus;
    private String analystId;
    private String analystNotes;
    private Instant resolvedAt;
}
