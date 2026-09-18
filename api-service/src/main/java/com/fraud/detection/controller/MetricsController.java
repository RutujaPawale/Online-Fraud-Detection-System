package com.fraud.detection.controller;

import com.fraud.detection.dto.ModelMetricsResponse;
import com.fraud.detection.service.MlClientService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/metrics")
@RequiredArgsConstructor
public class MetricsController {

    private final MlClientService mlClientService;

    @GetMapping
    public ResponseEntity<ModelMetricsResponse> getMetrics() {
        ModelMetricsResponse metrics = mlClientService.getModelMetrics();
        return ResponseEntity.ok(metrics);
    }
}
