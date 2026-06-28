/// 蒙特卡洛 π 估计 — 使用 Tempest v3 CSPRNG
///
/// 用法:
///   cargo run --example pi_estimation --release
use tempest_rng::TempestRng;
use rand_core::RngCore;

fn main() {
    let n = 10_000_000u64;
    let mut rng = TempestRng::from(42u64);
    let mut inside = 0u64;

    for _ in 0..n {
        let x = (rng.next_u64() >> 11) as f64 * (1.0 / (1u64 << 53) as f64);
        let y = (rng.next_u64() >> 11) as f64 * (1.0 / (1u64 << 53) as f64);
        if x * x + y * y < 1.0 {
            inside += 1;
        }
    }

    let pi = 4.0 * inside as f64 / n as f64;
    println!("π ≈ {:.6} (误差: {:.2e})", pi, (pi - std::f64::consts::PI).abs());
}
