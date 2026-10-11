"""Exercise install.sh command construction with mocked tools and dependencies.

Run: python3 -m unittest discover -s tests -p test_install.py
No package managers, compilers, network requests, or system installs are run.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "install.sh"

class InstallScriptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ocl-install-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / "project with spaces"
        self.project.mkdir()
        shutil.copyfile(SCRIPT, self.project / "install.sh")
        self.tools = self.root / "tools"
        self.tools.mkdir()
        self.log = self.root / "commands.jsonl"
        self.archive_dir = self.root / "archives"
        self.archive_dir.mkdir()
        self.env = {k: v for k, v in os.environ.items()
                    if not k.startswith("OCL_") and k not in {"VIRTUAL_ENV", "CONDA_PREFIX", "BOOST_ROOT", "CMAKE_ARGS", "CMAKE_PREFIX_PATH"}}
        (self.tools / "bash").symlink_to(shutil.which("bash"))
        (self.tools / "mkdir").symlink_to(shutil.which("mkdir"))
        self.env.update(PATH=str(self.tools) + os.pathsep + os.environ["PATH"],
                        TMPDIR=str(self.archive_dir), OCL_TEST_COMMAND_LOG=str(self.log),
                        OCL_TEST_PURELIB=str(self.root / "site packages"),
                        OCL_TEST_PYBIND=str(self.root / "pybind11 cmake"),
                        OCL_TEST_BREW_PREFIX=str(self.root / "brew boost"),
                        OCL_TEST_NATIVE_BOOST="C:/checkout/build/deps/boost/lib/native/include")
        self.python = self.tools / "selected python"
        self.stub(self.python, "python")
        self.stub(self.tools / "python3", "python")
        self.stub(self.tools / "cmake", "cmake")
        self.stub(self.tools / "curl", "curl")
        self.stub(self.tools / "tar", "tar")
        self.stub(self.tools / "nproc", "nproc")
        self.stub(self.tools / "sysctl", "sysctl")
        self.stub(self.tools / "apt", "apt")
        self.stub(self.tools / "sudo", "sudo")
        self.stub(self.tools / "choco", "choco")
        self.stub(self.tools / "cygpath", "cygpath")

    def stub(self, path, tool):
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.is_symlink():
            path.unlink()
        source = "#!" + sys.executable + "\n" + '''import json, os, pathlib, sys
name = TOOL
args = sys.argv[1:]
with open(os.environ["OCL_TEST_COMMAND_LOG"], "a") as stream:
    stream.write(json.dumps({"tool": name, "exe": sys.argv[0], "args": args,
                             "cmake_args": os.environ.get("CMAKE_ARGS"),
                             "openmp_prefix": os.environ.get("OPENMP_PREFIX_MACOS")}) + "\\n")
if name == "python":
    if args[:1] == ["-c"]:
        print(os.environ["OCL_TEST_PURELIB"] if "sysconfig" in args[1] else sys.argv[0])
    elif args == ["-m", "pybind11", "--cmakedir"]:
        if os.environ.get("OCL_TEST_NO_PYBIND"):
            sys.exit(1)
        print(os.environ["OCL_TEST_PYBIND"])
elif name in ("nproc", "sysctl"):
    print("2")
elif name == "tar" and args[:1] == ["-zxf"]:
    destination = pathlib.Path(args[args.index("-C") + 1])
    header = destination / "boost_1_87_0" / "boost" / "version.hpp"
    header.parent.mkdir(parents=True, exist_ok=True)
    header.write_text("#define BOOST_VERSION 108700\\n")
elif name == "brew":
    if args == ["--prefix", "boost"]:
        print(os.environ["OCL_TEST_BREW_PREFIX"])
    elif args == ["--prefix", "libomp"]:
        print(os.environ["OCL_TEST_LIBOMP_PREFIX"])
elif name == "lipo":
    if args[:2] != ["-verify_arch", os.environ.get("OCL_TEST_LIBOMP_ARCH", "arm64")]:
        sys.exit(1)
elif name == "cygpath":
    print(os.environ["OCL_TEST_NATIVE_BOOST"])
elif name == "nuget" and args[:2] == ["install", "boost"]:
    if not os.environ.get("OCL_TEST_NUGET_NO_HEADERS"):
        destination = pathlib.Path(args[args.index("-OutputDirectory") + 1])
        header = destination / "boost" / "lib" / "native" / "include" / "boost" / "version.hpp"
        header.parent.mkdir(parents=True, exist_ok=True)
        header.write_text("#define BOOST_VERSION 108700\\n")
elif name == "choco" and args[:2] == ["install", "nuget.commandline"]:
    target = pathlib.Path(sys.argv[0]).parent / "nuget"
    target.write_text(pathlib.Path(sys.argv[0]).read_text().replace("name = 'choco'", "name = 'nuget'"))
    target.chmod(0o755)
elif name == "curl":
    pathlib.Path(args[args.index("--output") + 1]).write_bytes(b"mock boost archive")
'''.replace("TOOL", repr(tool))
        path.write_text(source)
        path.chmod(0o755)

    def run_install(self, *options, success=True, env=None):
        result = subprocess.run(["bash", "install.sh", *options], cwd=self.project,
                                env={**self.env, **(env or {})}, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def commands(self, tool):
        if not self.log.exists():
            return []
        return [entry for entry in map(json.loads, self.log.read_text().splitlines()) if entry["tool"] == tool]

    def package_commands(self):
        result = []
        for tool in ("apt", "dnf", "yum", "sudo"):
            for entry in self.commands(tool):
                result.append(entry["args"] if tool == "sudo" else [tool, *entry["args"]])
        return result

    def configured_cmake(self):
        return [c for c in self.commands("cmake") if "--build" not in c["args"] and "--install" not in c["args"]][0]["args"]

    def test_direct_build_uses_selected_python_pybind_and_preserves_spaced_options(self):
        prefix = self.root / "boost headers"
        prefix.mkdir()
        self.run_install("--build-library", "python", "--python-executable", str(self.python),
                         "--python-prefix", "/python prefix", "--boost-prefix", str(prefix),
                         "--disable-openmp", "--cmake-generator", "Unix Makefiles",
                         "--cmake-generator-platform", "x64", "--install", "--install-prefix", "/install prefix")
        args = self.configured_cmake()
        for arg in ["-DPython3_EXECUTABLE=" + str(self.python), "-Dpybind11_DIR=" + self.env["OCL_TEST_PYBIND"],
                    "-DPython3_ROOT_DIR=/python prefix", "-DBOOST_ROOT=" + str(prefix), "-DUSE_OPENMP=OFF",
                    "CMAKE_INSTALL_PREFIX=/install prefix"]:
            self.assertIn(arg, args)
        self.assertEqual(args[args.index("-G") + 1], "Unix Makefiles")
        self.assertEqual(args[args.index("-A") + 1], "x64")
        self.assertIn(["--install", "."], [c["args"] for c in self.commands("cmake")])
        self.assertFalse(any(c["args"][:2] == ["-m", "pip"] for c in self.commands("python")))

    def test_direct_build_uses_selected_python_install_destination(self):
        self.run_install("--build-library", "python", "--python-executable", str(self.python))
        self.assertIn("CMAKE_INSTALL_PREFIX=" + self.env["OCL_TEST_PURELIB"], self.configured_cmake())

    def test_missing_python_fails_before_configure(self):
        result = self.run_install("--build-library", "python", "--python-executable", "/not/a/python", success=False)
        self.assertIn("Cannot find Python executable", result.stderr)
        self.assertEqual(self.commands("cmake"), [])

    def test_system_pybind_discovery_remains_available(self):
        self.run_install("--build-library", "python", "--python-executable", str(self.python),
                         env={"OCL_TEST_NO_PYBIND": "1"})
        self.assertFalse(any(a.startswith("-Dpybind11_DIR=") for a in self.configured_cmake()))

    def test_pip_delegates_build_dependencies_and_forwards_all_build_options(self):
        self.run_install("--build-library", "python", "--python-pip-install", "--python-executable", str(self.python),
                         "--build-type", "debug", "--disable-openmp", "--python-prefix", "/python prefix",
                         "--boost-prefix", "/boost prefix", "--cmake-generator", "Unix Makefiles",
                         "--cmake-generator-platform", "ARM64", env={"CMAKE_ARGS": "-DUSER_OPTION=ON"})
        pip = [c for c in self.commands("python") if c["args"][:2] == ["-m", "pip"]]
        self.assertEqual(len(pip), 1)
        args = pip[0]["args"]
        for arg in ["--config-settings=cmake.build-type=Debug", "--config-settings=cmake.define.USE_OPENMP=OFF",
                    "--config-settings=cmake.define.Python3_EXECUTABLE=" + str(self.python),
                    "--config-settings=cmake.define.Python3_ROOT_DIR=/python prefix",
                    "--config-settings=cmake.define.BOOST_ROOT=/boost prefix",
                    "--config-settings=cmake.args=-G", "--config-settings=cmake.args=Unix Makefiles",
                    "--config-settings=cmake.args=-A", "--config-settings=cmake.args=ARM64"]:
            self.assertIn(arg, args)
        self.assertEqual(pip[0]["cmake_args"], "-DUSER_OPTION=ON")
        self.assertEqual(args[-1], ".")
        self.assertEqual(self.commands("cmake"), [])

    def mock_macos_libomp(self):
        prefix = self.root / "brew libomp"
        for relative in ("include/omp.h", "lib/libomp.dylib"):
            path = prefix / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
        self.env["OCL_TEST_LIBOMP_PREFIX"] = str(prefix)
        # Mock installation, architecture inspection and writes to /tmp/libomp.
        for tool in ("brew", "lipo", "ln", "mkdir"):
            self.stub(self.tools / tool, tool)
        return prefix

    def test_macos_libomp_uses_installed_prefix_without_requiring_a_bottle(self):
        prefix = self.mock_macos_libomp()
        for architecture in ("arm64", "x86_64"):
            with self.subTest(architecture=architecture):
                if self.log.exists():
                    self.log.unlink()
                self.run_install("--install-ci-deps", "--install-boost-from-repo", "--platform", "macos",
                                 "--macos-architecture", architecture,
                                 env={"OCL_TEST_LIBOMP_ARCH": architecture})
                self.assertEqual([c["args"] for c in self.commands("brew")],
                                 [["install", "libomp"], ["--prefix", "libomp"]])
                self.assertEqual(self.commands("lipo")[0]["args"],
                                 ["-verify_arch", architecture, str(prefix / "lib/libomp.dylib")])
                self.assertEqual(self.commands("ln")[0]["args"],
                                 ["-sfn", str(prefix), "/tmp/libomp/libomp/fixed"])
                self.assertEqual(self.commands("tar"), [])

    def test_macos_libomp_rejects_wrong_architecture_before_building(self):
        self.mock_macos_libomp()
        result = self.run_install("--install-ci-deps", "--platform", "macos", "--macos-architecture", "x86_64",
                                  "--build-library", "cxx", success=False,
                                  env={"OCL_TEST_LIBOMP_ARCH": "arm64"})
        self.assertIn("Installed libomp does not support x86_64", result.stderr)
        self.assertEqual(self.commands("ln"), [])
        self.assertEqual(self.commands("cmake"), [])

    def test_macos_libomp_rejects_missing_library(self):
        prefix = self.mock_macos_libomp()
        (prefix / "lib/libomp.dylib").unlink()
        result = self.run_install("--install-ci-deps", "--platform", "macos", success=False)
        self.assertIn("Cannot find libomp library", result.stderr)
        self.assertEqual(self.commands("ln"), [])

    def test_python_test_uses_same_selected_interpreter(self):
        (self.project / "examples" / "python").mkdir(parents=True)
        self.run_install("--build-library", "python", "--python-executable", str(self.python), "--test")
        self.assertEqual(self.commands("python")[-1]["args"], ["test.py"])
        self.assertEqual(self.commands("python")[-1]["exe"], str(self.python))

    def test_linux_direct_system_dependencies_include_headers(self):
        self.stub(self.tools / "sudo", "sudo")
        self.run_install("--install-system-deps", "--build-library", "python", "--platform", "linux")
        apt_args = self.package_commands()
        self.assertIn(["apt", "install", "-y", "--no-install-recommends", "pybind11-dev"], apt_args)
        self.assertIn(["apt", "install", "-y", "--no-install-recommends", "python3", "python3-dev"], apt_args)

    def test_pip_build_does_not_install_system_python_or_binding_headers(self):
        self.stub(self.tools / "sudo", "sudo")
        self.run_install("--install-system-deps", "--build-library", "python", "--platform", "linux",
                         "--python-pip-install", "--python-executable", str(self.python))
        packages = [p for args in self.package_commands() for p in args]
        self.assertNotIn("pybind11-dev", packages)
        self.assertNotIn("python3-dev", packages)
        self.assertNotIn("python3", packages)

    def test_standalone_repository_flag_does_not_install_on_any_platform(self):
        for platform in ("linux", "macos", "windows"):
            with self.subTest(platform=platform):
                self.run_install("--install-boost-from-repo", "--platform", platform)
        self.assertEqual(self.package_commands(), [])
        for tool in ("brew", "choco", "nuget", "curl", "tar"):
            self.assertEqual(self.commands(tool), [])

    def test_repository_and_system_dependencies_do_not_duplicate_boost_install(self):
        self.run_install("--install-boost-from-repo", "--install-system-deps", "--platform", "linux")
        commands = self.package_commands()
        self.assertEqual(sum("libboost-dev" in args for args in commands), 1)
        self.assertEqual(sum(args == ["apt", "update"] for args in commands), 1)

    def test_repository_flag_with_ci_dependencies_does_not_install_boost(self):
        self.run_install("--install-boost-from-repo", "--install-ci-deps", "--platform", "linux")
        commands = self.package_commands()
        self.assertEqual(sum("libboost-dev" in args for args in commands), 0)
        self.assertEqual(sum(args == ["apt", "update"] for args in commands), 1)

    def test_python_system_dependencies_require_repository_flag_for_boost(self):
        self.run_install("--install-system-deps", "--build-library", "python", "--python-executable", str(self.python))
        self.assertFalse(any("libboost-dev" in args for args in self.package_commands()))
        self.assertNotIn("-UBOOST_ROOT", self.configured_cmake())

    def test_plain_python_build_never_installs_dependencies(self):
        self.run_install("--build-library", "python", "--python-executable", str(self.python))
        self.assertEqual(self.package_commands(), [])
        self.assertEqual(self.commands("curl"), [])

    def test_macos_repository_installs_boost_once_with_system_dependencies(self):
        self.stub(self.tools / "brew", "brew")
        self.run_install("--install-boost-from-repo", "--install-system-deps", "--build-library", "python", "--python-executable", str(self.python), "--platform", "macos")
        self.assertEqual(sum(c["args"] == ["install", "boost"] for c in self.commands("brew")), 1)
        self.assertFalse(any(a.startswith("-DBOOST_ROOT=") for a in self.configured_cmake()))

    def test_windows_repository_installs_versionless_headers_only_nuget(self):
        self.stub(self.tools / "nuget", "nuget")
        self.run_install("--install-system-deps", "--install-boost-from-repo", "--platform", "windows", "--build-library", "python", "--python-executable", str(self.python))
        args = self.commands("nuget")[0]["args"]
        self.assertEqual(args[:2], ["install", "boost"])
        self.assertIn("-ExcludeVersion", args)
        self.assertIn("-NonInteractive", args)
        self.assertNotIn("-Version", args)
        self.assertIn("-DBOOST_ROOT=" + self.env["OCL_TEST_NATIVE_BOOST"], self.configured_cmake())
        self.assertEqual(self.commands("curl"), [])

    def test_windows_nuget_prefix_is_native_in_pip_config_settings(self):
        self.stub(self.tools / "nuget", "nuget")
        self.stub(self.tools / "cygpath", "cygpath")
        native_prefix = "D:/checkout with spaces/build/deps/boost/lib/native/include"
        self.run_install("--install-system-deps", "--install-boost-from-repo", "--platform", "windows", "--build-library", "python",
                         "--python-pip-install", "--python-executable", str(self.python),
                         env={"OCL_TEST_NATIVE_BOOST": native_prefix})
        self.assertEqual(self.commands("cygpath")[0]["args"],
                         ["-m", str(self.project / "build/deps/boost/lib/native/include")])
        pip = [c for c in self.commands("python") if c["args"][:2] == ["-m", "pip"]][0]
        self.assertIn("--config-settings=cmake.define.BOOST_ROOT=" + native_prefix, pip["args"])

    def test_source_and_repository_flags_remain_accepted_together(self):
        self.run_install("--install-boost", "--install-boost-from-repo")
        self.assertEqual(len(self.commands("tar")), 1)
        self.assertEqual(self.package_commands(), [])

    def test_windows_ci_dependencies_with_repository_flag_do_not_install_boost(self):
        self.run_install("--install-ci-deps", "--install-boost-from-repo", "--platform", "windows")
        self.assertEqual([c["args"] for c in self.commands("choco")], [["install", "curl", "--no-progress"]])
        self.assertEqual(self.commands("nuget"), [])

    def test_cpp_branch_remains_independent_of_python(self):
        self.run_install("--build-library", "cxx", "--disable-openmp", "--install")
        self.assertIn("BUILD_CXX_LIB=ON", self.configured_cmake())
        self.assertIn("-DUSE_OPENMP=OFF", self.configured_cmake())
        self.assertEqual(self.commands("python"), [])

if __name__ == "__main__":
    unittest.main()
