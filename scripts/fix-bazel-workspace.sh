set -e
cd /root/aosp/kernel/platform/kernel-6.12

# kernel/manifest's build/kernel project defines three linkfiles; without MODULE.bazel
# and WORKSPACE.bzlmod bazel refuses to resolve the workspace ("Unable to determine root
# of repository").
[ -e MODULE.bazel ] || ln -sfn build/kernel/kleaf/bzlmod/bazel.MODULE.bazel MODULE.bazel
[ -e WORKSPACE.bzlmod ] || ln -sfn build/kernel/kleaf/bzlmod/bazel.WORKSPACE.bzlmod WORKSPACE.bzlmod
[ -e tools/bazel ] || ln -sfn ../build/kernel/kleaf/bazel.sh tools/bazel

echo "=== workspace root files ==="
ls -l MODULE.bazel WORKSPACE.bzlmod tools/bazel
echo "=== targets present? ==="
ls build/kernel/kleaf/bzlmod/bazel.MODULE.bazel build/kernel/kleaf/bzlmod/bazel.WORKSPACE.bzlmod 2>&1
