//! Concrete path sampler implementations.
//!
//! OCP: add new stochastic processes by implementing PathSampler trait.

use rand::Rng;
use stratos_core::traits::PathSampler;

/// Geometric Brownian Motion (GBM) sampler.
///
/// Models: dS = μS·dt + σS·dW
/// Used for equity price simulation.
pub struct GbmSampler {
    drift: f64,     // annualized drift (μ)
    volatility: f64, // annualized volatility (σ)
    dt: f64,         // time step size (e.g., 1/252 for daily)
}

impl GbmSampler {
    pub fn new(drift: f64, volatility: f64, dt: f64) -> Self {
        Self { drift, volatility, dt }
    }
}

impl PathSampler for GbmSampler {
    fn sample_path(&self, initial: f64, steps: usize) -> Vec<f64> {
        let mut rng = rand::thread_rng();
        let mut path = Vec::with_capacity(steps + 1);
        path.push(initial);

        let mut value = initial;
        for _ in 0..steps {
            // Box-Muller for normal random
            let u1: f64 = rng.gen::<f64>().max(1e-15);
            let u2: f64 = rng.gen();
            let z = (-2.0 * u1.ln()).sqrt() * (2.0 * std::f64::consts::PI * u2).cos();

            // GBM step: S(t+dt) = S(t) * exp((μ - σ²/2)·dt + σ·√dt·Z)
            value *= ((self.drift - 0.5 * self.volatility * self.volatility) * self.dt
                + self.volatility * self.dt.sqrt() * z)
                .exp();
            path.push(value);
        }
        path
    }
}

/// Mean-Reverting (Ornstein-Uhlenbeck) sampler.
///
/// Models: dX = θ(μ - X)·dt + σ·dW
/// Used for interest rates, commodities, spread modeling.
pub struct MeanRevertingSampler {
    long_term_mean: f64, // μ
    speed: f64,           // θ (mean reversion speed)
    volatility: f64,      // σ
}

impl MeanRevertingSampler {
    pub fn new(long_term_mean: f64, speed: f64, volatility: f64) -> Self {
        Self {
            long_term_mean,
            speed,
            volatility,
        }
    }
}

impl PathSampler for MeanRevertingSampler {
    fn sample_path(&self, initial: f64, steps: usize) -> Vec<f64> {
        let mut rng = rand::thread_rng();
        let mut path = Vec::with_capacity(steps + 1);
        path.push(initial);

        let dt = 1.0 / 252.0; // daily steps
        let mut value = initial;

        for _ in 0..steps {
            let u1: f64 = rng.gen::<f64>().max(1e-15);
            let u2: f64 = rng.gen();
            let z = (-2.0 * u1.ln()).sqrt() * (2.0 * std::f64::consts::PI * u2).cos();

            // OU step
            value += self.speed * (self.long_term_mean - value) * dt
                + self.volatility * dt.sqrt() * z;
            path.push(value);
        }
        path
    }
}

/// Jump-Diffusion (Merton) sampler.
///
/// Models: dS = μS·dt + σS·dW + J·dN (Poisson jumps)
/// Used for tail risk simulation, crash modeling.
pub struct JumpDiffusionSampler {
    drift: f64,
    volatility: f64,
    jump_intensity: f64,  // λ — average jumps per year
    jump_mean: f64,       // average jump size
    jump_std: f64,        // jump size std dev
    dt: f64,
}

impl JumpDiffusionSampler {
    pub fn new(
        drift: f64,
        volatility: f64,
        jump_intensity: f64,
        jump_mean: f64,
        jump_std: f64,
        dt: f64,
    ) -> Self {
        Self {
            drift,
            volatility,
            jump_intensity,
            jump_mean,
            jump_std,
            dt,
        }
    }
}

impl PathSampler for JumpDiffusionSampler {
    fn sample_path(&self, initial: f64, steps: usize) -> Vec<f64> {
        let mut rng = rand::thread_rng();
        let mut path = Vec::with_capacity(steps + 1);
        path.push(initial);

        let mut value = initial;
        for _ in 0..steps {
            // Diffusion component (GBM)
            let u1: f64 = rng.gen::<f64>().max(1e-15);
            let u2: f64 = rng.gen();
            let z = (-2.0 * u1.ln()).sqrt() * (2.0 * std::f64::consts::PI * u2).cos();

            let diffusion = ((self.drift - 0.5 * self.volatility * self.volatility) * self.dt
                + self.volatility * self.dt.sqrt() * z)
                .exp();

            // Jump component (Poisson arrival)
            let jump_prob = self.jump_intensity * self.dt;
            let jump = if rng.gen::<f64>() < jump_prob {
                // Generate jump size (log-normal)
                let u3: f64 = rng.gen::<f64>().max(1e-15);
                let u4: f64 = rng.gen();
                let z_j = (-2.0 * u3.ln()).sqrt() * (2.0 * std::f64::consts::PI * u4).cos();
                (self.jump_mean + self.jump_std * z_j).exp()
            } else {
                1.0
            };

            value *= diffusion * jump;
            path.push(value);
        }
        path
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_gbm_path_length() {
        let sampler = GbmSampler::new(0.1, 0.2, 1.0 / 252.0);
        let path = sampler.sample_path(100.0, 252);
        assert_eq!(path.len(), 253); // initial + 252 steps
    }

    #[test]
    fn test_gbm_positive_values() {
        let sampler = GbmSampler::new(0.1, 0.2, 1.0 / 252.0);
        let path = sampler.sample_path(100.0, 1000);
        assert!(path.iter().all(|&v| v > 0.0), "GBM should produce positive values");
    }

    #[test]
    fn test_mean_reverting() {
        let sampler = MeanRevertingSampler::new(100.0, 2.0, 0.1);
        // Start far from mean
        let path = sampler.sample_path(50.0, 1000);
        let terminal = path.last().unwrap();
        // Should revert closer to 100
        assert!(*terminal > 50.0, "Should revert toward long-term mean");
    }

    #[test]
    fn test_jump_diffusion() {
        let sampler = JumpDiffusionSampler::new(0.08, 0.2, 5.0, -0.05, 0.1, 1.0 / 252.0);
        let path = sampler.sample_path(100.0, 252);
        assert_eq!(path.len(), 253);
        assert!(path[0] == 100.0);
    }
}
