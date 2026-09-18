package com.fraud.detection.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.*;

import java.math.BigDecimal;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class MlScoreRequest {

    @JsonProperty("transaction_ref")
    private String transactionRef;

    @JsonProperty("transaction_amt")
    private BigDecimal transactionAmt;

    @JsonProperty("product_cd")
    private String productCd;

    @JsonProperty("card1")
    private String card1;

    @JsonProperty("card2")
    private String card2;

    @JsonProperty("card3")
    private String card3;

    @JsonProperty("card4")
    private String card4;

    @JsonProperty("card5")
    private String card5;

    @JsonProperty("card6")
    private String card6;

    @JsonProperty("addr1")
    private String addr1;

    @JsonProperty("addr2")
    private String addr2;

    @JsonProperty("dist1")
    private Double dist1;

    @JsonProperty("dist2")
    private Double dist2;

    @JsonProperty("p_emaildomain")
    private String pEmailDomain;

    @JsonProperty("r_emaildomain")
    private String rEmailDomain;

    @JsonProperty("device_type")
    private String deviceType;

    @JsonProperty("device_info")
    private String deviceInfo;

    @JsonProperty("browser_version")
    private String browserVersion;

    @JsonProperty("additional_features")
    private java.util.Map<String, Object> additionalFeatures;
}
