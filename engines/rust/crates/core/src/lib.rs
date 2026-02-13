//! STRATOS Core — shared types, traits, and math utilities.
//!
//! This crate defines the domain abstractions that ALL engine crates depend on.
//! It enforces Dependency Inversion: other crates depend on traits defined HERE.

pub mod error;
pub mod math;
pub mod traits;
pub mod types;
