package com.fraud.detection.dto;

import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.*;

import java.math.BigDecimal;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class TransactionRequest {

    @NotBlank(message = "transactionRef is required")
    private String transactionRef;

    @NotBlank(message = "userId is required")
    private String userId;

    @NotNull(message = "amount is required")
    @DecimalMin(value = "0.01", message = "amount must be greater than 0")
    private BigDecimal amount;

    @Builder.Default
    private String currency = "USD";

    @NotBlank(message = "productCd is required")
    private String productCd;

    private String card1;
    private String card2;
    private String card3;
    private String card4;
    private String card5;
    private String card6;

    private String addr1;
    private String addr2;
    private Double dist1;
    private Double dist2;

    @com.fasterxml.jackson.annotation.JsonProperty("pEmailDomain")
    @com.fasterxml.jackson.annotation.JsonAlias({"p_emaildomain", "pemailDomain"})
    private String pEmailDomain;

    @com.fasterxml.jackson.annotation.JsonProperty("rEmailDomain")
    @com.fasterxml.jackson.annotation.JsonAlias({"r_emaildomain", "remailDomain"})
    private String rEmailDomain;

    private String deviceType;
    private String deviceInfo;
    private String browserVersion;

    @com.fasterxml.jackson.annotation.JsonProperty("additionalFeatures")
    @com.fasterxml.jackson.annotation.JsonAlias({"additional_features", "additionalFeatures"})
    private java.util.Map<String, Object> additionalFeatures;
}
