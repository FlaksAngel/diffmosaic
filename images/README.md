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

The four current profiles depend on each project's committed `uv.lock`. They
install their declared `tests` or `dev` dependency group into `/opt`, rather
than a `.venv` inside `/workspace`. This matters because the mutation runner
replaces `/workspace` with a fresh read-only archive during every invocation.

## Controlled build procedure

For each profile, use a fresh source directory and replace the values below
with that profile's repository URL, head SHA, package list, group and tag.
`apt_packages` is normally empty; it records a reviewed system dependency such
as Click's `less` pager.

```powershell
git clone https://github.com/example/project.git C:\research\project-source
git -C C:\research\project-source checkout --detach <head-commit>
git -C C:\research\project-source rev-parse HEAD

docker build --pull=false `
  --build-arg APT_PACKAGES=<space-separated-reviewed-packages> `
  --build-arg UV_GROUP=<tests-or-dev> `
  --tag <image-tag> `
  --file C:\path\to\diffmosaic\images\Dockerfile.uv-locked `
  C:\research\project-source
```

The `rev-parse` output must equal the profile's `head_commit`. Review the
Docker build output and then prove that the image is available locally:

```powershell
docker image inspect <image-tag> `
  --format '{{if .RepoDigests}}{{index .RepoDigests 0}}{{else}}{{.Id}}{{end}}'
```

Copy the returned digest or image ID into `docker_image_identity`, copy the tag
into `docker_image`, change the subject's role from `candidate` to `study`, and
re-run `diffmosaic corpus-validate`. Only then may `mutate-run` be used.

## Limits

The profile's base-image tag is a build input, not a claim of reproducibility
by itself. The recorded final image digest or ID is the identity used by an
experiment. DiffMosaic neither pulls base images nor builds these recipes, and
does not execute a target project's Dockerfile.
