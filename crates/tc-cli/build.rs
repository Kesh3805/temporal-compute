use std::{env, path::PathBuf, process::Command};

fn main() {
    let root = PathBuf::from(env::var_os("CARGO_MANIFEST_DIR").unwrap_or_default()).join("../..");
    // Rebuild provenance when source, configuration or the checked-out revision changes.
    for path in [
        "crates",
        "Cargo.toml",
        "Cargo.lock",
        "rust-toolchain.toml",
        ".cargo",
        ".git/HEAD",
        ".git/packed-refs",
        ".git/index",
        "scenarios",
        "scripts",
    ] {
        println!("cargo:rerun-if-changed={}", root.join(path).display());
    }
    let git = |args: &[&str]| {
        Command::new("git")
            .args(args)
            .current_dir(&root)
            .output()
            .ok()
            .filter(|out| out.status.success())
            .map(|out| String::from_utf8_lossy(&out.stdout).trim().to_owned())
    };
    if let Some(head) = git(&["symbolic-ref", "-q", "HEAD"]) {
        println!(
            "cargo:rerun-if-changed={}",
            root.join(".git").join(head).display()
        );
    }
    if let Some(commit) = git(&["rev-parse", "HEAD"]) {
        println!("cargo:rustc-env=TC_BUILD_GIT_COMMIT={commit}");
    }
    if let Some(status) = git(&["status", "--porcelain", "--untracked-files=normal"]) {
        println!("cargo:rustc-env=TC_BUILD_GIT_DIRTY={}", !status.is_empty());
    }
    if let Some(version) = Command::new(env::var_os("RUSTC").unwrap_or_else(|| "rustc".into()))
        .arg("--version")
        .output()
        .ok()
        .filter(|out| out.status.success())
    {
        println!(
            "cargo:rustc-env=TC_BUILD_RUSTC={}",
            String::from_utf8_lossy(&version.stdout).trim()
        );
    }
}
