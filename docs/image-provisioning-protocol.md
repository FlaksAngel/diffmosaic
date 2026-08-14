# Image-provisioning protocol

An image is part of an experiment's environment. Its preparation is separated
from DiffMosaic's mutation runner because building an image can download
dependencies and run build hooks.

## Input review

Before a build, check all of the following:

1. the source URL and commit match `corpus/pilot-v0.1.json`;
2. the profile refers to the same `head_commit` and has `status: unbuilt`;
3. the source checkout contains the committed `uv.lock` file;
4. any profile `apt_packages` are necessary for the declared test command and
   have been reviewed as package names rather than copied from target code;
5. a non-null `setuptools_scm_pretend_version` is consistent with the exact
   source revision's reviewed version scheme; it is not an arbitrary build
   environment variable;
6. the Dockerfile has been read and contains no unreviewed project-specific
   command; and
7. the build machine and Docker daemon are approved for this work.

## Build and qualification

Build with the source repository itself as the context, not the DiffMosaic
repository. The generic recipe installs dependencies outside `/workspace` so a
fresh archived checkout can later be mounted there read-only. Build with
`--pull=false`; this prevents Docker from silently replacing the selected base
image during an experiment.

Do not classify a container image as trusted merely because it built. Run the
planned test command once manually in a disposable container, inspect its
identity, and review the build/test logs for credentials. Record the image tag
and digest or ID in the corpus manifest. Then change `role` to `study` and
freeze a new corpus version before interpreting mutation results.

## Separation of responsibilities

| Step | DiffMosaic | Experimenter |
| --- | --- | --- |
| Select source SHA | validates manifest | reviews source/project license |
| Build image | never | runs reviewed recipe in approved Docker environment |
| Identify image | records runtime identity | inspects digest or ID |
| Execute mutations | invokes only supplied local image | authorises target/test command |

This separation avoids treating a developer tool as authority to run unknown
installation logic. It also makes an eventual paper's environment description
auditable.
