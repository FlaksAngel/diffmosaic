# Candidate-image recipes

These files are build specifications, not a feature that DiffMosaic executes.
They exist so an experimenter can review and reproduce the image-preparation
step before a candidate becomes an executable study subject.

## Preconditions

- Docker is installed and its daemon is running on the experiment machine.
- The source repository is public, authorised for analysis, and checked out at
  the `head_commit` in `profiles-v0.1.json`.
- The checkout is treated as build input only. Do not use your personal working
  tree or any directory containing credentials.

`profiles-v0.1.json` retains the original pilot recipes. `profiles-v0.2.json`
tracks the preliminary study candidates. A profile either uses a committed
`uv.lock` or a reviewed project requirements file; any candidate without a
reviewed recipe is explicitly `deferred`. Every recipe installs dependencies
into `/opt`, rather than a `.venv` inside `/workspace`. This matters because
the mutation runner replaces `/workspace` with a fresh read-only archive during
every invocation.

## Controlled build procedure

For each `unbuilt` profile, use a fresh source directory checked out at its
head SHA. The `uv` recipe needs `UV_GROUP`; the requirements recipe needs
`REQUIREMENTS_FILE`. The `uv` recipe also accepts `apt_packages` and
`setuptools_scm_pretend_version` where its reviewed profile declares them.

```powershell
git clone https://github.com/example/project.git C:\research\project-source
git -C C:\research\project-source checkout --detach <head-commit>
git -C C:\research\project-source rev-parse HEAD

docker build --pull=false `
  --build-arg UV_GROUP=<profile-value> `
  --tag <image-tag> `
  --file C:\path\to\diffmosaic\images\<profile-dockerfile> `
  C:\research\project-source
```

For `Dockerfile.pip-requirements`, replace `UV_GROUP` with
`REQUIREMENTS_FILE=<profile-value>`. When an `uv` profile declares
`setuptools_scm_pretend_version`, also pass
`--build-arg SETUPTOOLS_SCM_PRETEND_VERSION=<profile-value>`. This is a
reviewed, version-scheme-specific build input for projects whose package
metadata depends on absent Git history; it is never inferred at build time.

The `rev-parse` output must equal the profile's `head_commit`. Review the
Docker build output and then prove that the image is available locally:

```powershell
docker image inspect <image-tag> `
  --format '{{if .RepoDigests}}{{index .RepoDigests 0}}{{else}}{{.Id}}{{end}}'
```

Copy the returned digest or image ID into `docker_image_identity`, copy the tag
into `docker_image`, change the subject's role from `candidate` to `study`, and
re-run `diffmosaic corpus-validate`. Only then may the run be treated as study
evidence. A `built` profile records that an image was prepared locally for
development qualification; it is not, by itself, a frozen study subject.

## Limits

The profile's base-image tag is a build input, not a claim of reproducibility
by itself. The recorded final image digest or ID is the identity used by an
experiment. DiffMosaic neither pulls base images nor builds these recipes, and
does not execute a target project's Dockerfile.
