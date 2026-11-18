set -e
cd /root/aosp

# Project set and revisions mirror kernel/manifest's default.xml on branch
# common-android16-6.12 (6.12 is the Android 16 LTS line; android17 only ships 6.18).
# Paths are re-rooted under kernel/platform/kernel-6.12/ so the Kleaf workspace sits where
# TARGET_KERNEL_SOURCE expects it. tools/bazel comes from kernel/build's linkfile.
REV="android16-6.12"

mkdir -p .repo/local_manifests
cat > .repo/local_manifests/kernel.xml <<XML
<?xml version="1.0" encoding="UTF-8"?>
<manifest>
  <project path="kernel/platform/kernel-6.12/build/kernel"
           name="kernel/build" revision="$REV" remote="aosp">
    <linkfile src="kleaf/bazel.sh"
              dest="kernel/platform/kernel-6.12/tools/bazel" />
    <linkfile src="kleaf/bzlmod/bazel.MODULE.bazel"
              dest="kernel/platform/kernel-6.12/MODULE.bazel" />
    <linkfile src="kleaf/bzlmod/bazel.WORKSPACE.bzlmod"
              dest="kernel/platform/kernel-6.12/WORKSPACE.bzlmod" />
  </project>

  <project path="kernel/platform/kernel-6.12/common"
           name="kernel/common" revision="$REV" remote="aosp" />

  <project path="kernel/platform/kernel-6.12/prebuilts/kernel-build-tools"
           name="kernel/prebuilts/build-tools" revision="$REV" remote="aosp" />
  <project path="kernel/platform/kernel-6.12/prebuilts/build-tools"
           name="platform/prebuilts/build-tools" remote="aosp" />
  <project path="kernel/platform/kernel-6.12/prebuilts/clang/host/linux-x86"
           name="platform/prebuilts/clang/host/linux-x86" remote="aosp" />
  <project path="kernel/platform/kernel-6.12/prebuilts/rust"
           name="platform/prebuilts/rust" remote="aosp" />
  <project path="kernel/platform/kernel-6.12/tools/mkbootimg"
           name="platform/system/tools/mkbootimg" remote="aosp" />
</manifest>
XML

echo "== local_manifest =="
cat .repo/local_manifests/kernel.xml

export http_proxy=http://127.0.0.1:7897
export https_proxy=$http_proxy
git config --global http.proxy "$http_proxy"
git config --global https.proxy "$https_proxy"

echo "== syncing =="
repo sync -c --no-tags --no-clone-bundle --force-sync -j4 \
    kernel/platform/kernel-6.12/build/kernel \
    kernel/platform/kernel-6.12/common \
    kernel/platform/kernel-6.12/prebuilts/kernel-build-tools \
    kernel/platform/kernel-6.12/prebuilts/build-tools \
    kernel/platform/kernel-6.12/prebuilts/clang/host/linux-x86 \
    kernel/platform/kernel-6.12/prebuilts/rust \
    kernel/platform/kernel-6.12/tools/mkbootimg

echo "== workspace =="
ls kernel/platform/kernel-6.12/
ls -l kernel/platform/kernel-6.12/tools/bazel 2>/dev/null || echo "NO tools/bazel"
