# Track D — registered corpus asset preparation

Status: draft preparation only. This document scopes later asset construction; no scene files, images, references or comparative outcomes are produced here. It depends on the pending [TC-R1E3 selection PR #14](https://github.com/Kesh3805/temporal-compute/pull/14), whose PASS is retained in scientific [run 37578416061](https://github.com/Kesh3805/temporal-compute/actions/runs/37578416061). Production integration waits for its reviewed selection record on main. E2 remains FAIL TO QUALIFY due to incomplete evidence, not an observed PBRT failure.

Related research issue: [#9](https://github.com/Kesh3805/temporal-compute/issues/9), which remains open. Preserve the [original protocol](../preregistration.md), original research gates and historical evidence. Asset-manifest acceptance is a prerequisite to the separate execution freeze, not a substitute for it.

## Corpus contract to implement

Construct ten independently specified variants: two each in uniformly noisy, highly specular, simple diffuse, motion-heavy and adaptive-sampling-friendly families. Give every scene a stable scene identifier and three stable frame identifiers, at registered resolution 256x256. The eight paired seeds per scene give 80 scene/seed units and 240 frame renders per policy once execution is authorized. This is a planned corpus size, not existing data.

The future manifest must fix actual frame times and full per-frame transforms before asset acceptance. Static families repeat static geometry across the three fixed frames with distinct protocol-defined streams; motion-heavy scenes use independently positioned static geometry to change visibility. No temporal reuse or motion blur is introduced. Intended family challenges are independent design rationales, not measured claims about noise or controller advantage.

Before implementation, review and freeze the shared scene/frame manifest and stream-identifier schema with Tracks A and F. For each scene/frame bind exact geometry, camera transform/projection, units, material parameters, light parameters, exposure-independent rendering settings, family membership and frame definition. Every input asset, generated scene file and procedural generator receives a content hash; external assets also retain provenance URL, author, license text/identifier and redistribution permission. Pin generator/dependency revisions and parameters so reconstruction is auditable. A content hash alone is not licensing evidence.

## Selected kernel and feature boundary

Target the E3-selected PBRT `b4ce9687e6c695f5582997c61b0c66cf064bdb4a`, CPU float native path, with the existing E2 frozen surface-only envelope: spheres/triangle meshes; opaque diffuse, conductor and dielectric BSDFs; finite point/area and uniform environment lights; pinhole perspective camera; RGB Film; box reconstruction; unclamped radiance; native MIS/Russian roulette; maxdepth8; regularization disabled. Track A must freeze production stream mapping/configuration before integration. E2's 16-sample synthetic fixtures do not set reference or production sample limits.

Exclude media, subsurface, null interfaces, thin lens, textures, splats, normal/bump/displacement maps, specialized integrators, light-path tracing, bidirectional/photon transport, guiding, denoising, GPU and reconstruction beyond box. The asset validator must reject out-of-envelope configuration rather than silently admitting it. Any desired extension requires an explicit new pre-outcome research decision; this track does not grant one.

## Independence and acceptance

- Freeze all ten scene definitions and three frames per scene, with complete stable identifiers, family rationale and manifest hashes/licenses.
- Validate manifest completeness, reproducible scene generation, valid syntax and admitted features without policy performance data. Synthetic kernel correctness tests remain separate from this corpus.
- Do not select variants, move cameras, adjust light/material parameters, omit difficult cases or classify families using TC-versus-baseline quality/speed. No relative-performance pilot on primary scenes is permitted.
- Any later hardware/reference feasibility check may assess technical validity only, cannot optimize allocation parameters, and must preserve all failures. Freeze the corpus before Track F generates final reference streams.
- References and their convergence evidence remain Track F work: independently generated streams beginning at 8192 spp each, escalating to 16384 then 32768 as the original protocol requires. Corpus preparation cannot reduce those requirements to suit storage or runtime.

Unfilled manifests, missing license provenance or required features outside the envelope block asset acceptance. Preserve the original definitions and request an explicit versioned pre-outcome amendment if the corpus cannot satisfy the protocol; never replace a difficult scene after comparative outcomes. Final asset hashes will be bound with policies, references, metrics, analysis and hardware by `tc-r1-execution-preregistered` before any first comparison.
