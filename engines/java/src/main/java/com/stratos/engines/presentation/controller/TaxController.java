package com.stratos.engines.presentation.controller;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/v1/tax")
public class TaxController {

    @PostMapping("/optimize")
    public ResponseEntity<Map<String, Object>> optimizeTax(@RequestBody Map<String, Object> request) {
        // TODO: wire to use case
        return ResponseEntity.ok(Map.of("status", "not_implemented", "endpoint", "tax/optimize"));
    }

    @PostMapping("/simulate-gains")
    public ResponseEntity<Map<String, Object>> simulateGains(@RequestBody Map<String, Object> request) {
        return ResponseEntity.ok(Map.of("status", "not_implemented", "endpoint", "tax/simulate-gains"));
    }
}
