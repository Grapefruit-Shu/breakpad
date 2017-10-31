import argparse
import os
import platform
import pprint
import re
import shutil
import subprocess
import sys
import tempfile

current_dir = os.getcwd()
script_dir = os.path.dirname(os.path.abspath(__file__))

breakpad_dir = os.path.join(script_dir, 'breakpad')

linux = platform.system() == 'Linux'
osx = platform.system() == 'Darwin'
windows = platform.system() == 'Windows'


def build(version):
    if linux:
        cmd = ["./configure", "-prefix", os.path.join(breakpad_dir, version)]
        if not check_command(cmd, cwd=os.path.join(breakpad_dir, 'src')):
            print >> sys.stderr, "Failed to run configure in path: \"%s\"" % os.path.join(breakpad_dir, 'src')
            exit 1

        cmd = ["make", "install"]
        if not check_command(cmd, cwd=os.path.join(breakpad_dir, 'src')):
            print >> sys.stderr, "Failed to make install in path: \"%s\"" % os.path.join(breakpad_dir, 'src')
            exit 1
    elif osx:
        # Build breakpad framework
        breakpad_client_dir = os.path.join(breakpad_dir, 'src', 'src', 'client', 'mac')
        cmd = ['xcodebuild']

        if not check_command(cmd, cwd=breakpad_client_dir):
            print >> sys.stderr, "Failed to build Breakpad framework"
            exit 1
        breakpad_framework_build_path = os.path.join(breakpad_client_dir, 'Breakpad.Framework')
        dump_syms_dir = os.path.join(breakpad_dir, 'src', 'src', 'tools', 'mac', 'dump_syms')

        cmd = ['cp', '-R', breakpad_framework_build_path, dump_syms_dir]
        if not check_command(cmd):
            print >> sys.stderr, "Failed to copy breakpad framework to dump_syms directory."
            exit 1

        cmd = ['xcodebuild']
        if not check_command(cmd, cwd=dump_syms_dir):
            print >> sys.stderr, "Failed to build dump syms target"
            exit 1


def parseArguments():
    default_platform = {
        'Windows': 'win32',
        'Linux': 'linux-x64',
        'Darwin': 'osx'
    }.get(platform.system(), None)

    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", dest="output", default=current_dir, help="Path for the breakpad build directory, default=cwd")
    parser.add_argument("--depot_tools", dest="depot_tools", default=None, help="Location for depot tools checkout directory")
    parser.add_argument("-v", "--version", dest="version", default=None, help="Name to give build, default=git revision")
    parser.add_argument("-p", "--platform", dest="platform", default=default_platform, help="Name of platform to generate for ('linux-x64', 'win32', 'osx', or 'linux-android-armeabi-v7a'; default: host platform)")
    parser.add_argument("--clean", action='store_true', help="Clean the breakpad directory first. This will delete \"src\" directory and any changes within")
    parser.add_argument("--no-update", action='store_false', dest='update', help="Skip updating the breakpad repository first")
    parser.add_argument("--no-package", action='store_false', dest="package", help="Skip generating the package")
    args = parser.parse_args()

    if args.depot_tools is None:
        args.depot_tools = os.path.join(script_dir, 'depot_tools')

    #if args.version is None:
    #    args.version = getRevision(os.path.join(breakpad_dir, 'src'))

    return args


def getRevision(path):
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=path).strip()



def check_command(cmd, cwd=current_dir):
    if subprocess.call(cmd, cwd=cwd) != 0:
        print >> sys.stderr, 'Failed to run command: %s' % " ".join(cmd)
        return False
    return True


def initializeDepotTools(path):
    if not os.path.exists(path):
        cmd = ["git", "clone", "https://chromium.googlesource.com/chromium/tools/depot_tools.git", os.path.basename(path)]
        if not check_command(cmd, cwd=current_dir):
            return False
    os.environ['PATH'] = path + os.pathsep + os.environ['PATH']
    if windows:
        os.environ['DEPOT_TOOLS_WIN_TOOLCHAIN'] = '0'

    return True


def initializeRepository():
    if not os.path.exists(breakpad_dir):
        os.makedirs(breakpad_dir)

    cmd = ["fetch", "--nohooks", "breakpad"]
    if not check_command(cmd, cwd=breakpad_dir):
        print >> sys.stderr, "Could not fetch breakpad; it may have already been fetched"
        return False

    cmd = ["gclient", "sync", "-v"]
    if not check_command(cmd, cwd=breakpad_dir):
        print >> sys.stderr, "Could not do initial gclient sync"
        return False
    return True


def updateRevisions():
    print 'I would update revisions here.'
    return True


def updateRepository():
    print 'I would update repo here'
    return True


def createPackage(build_root, version, platform):
    archive_name = 'breakpad-' + version + '-' + platform + ".tar.gz"
    cmd = ['cmake', '-E', 'tar', 'cvzf', archive_name, version]

    if not check_command(cmd, cwd=build_root):
        print >> sys.stderr, 'Failed to create tarball'
    else:
        print "tarball created: %s" % os.path.join(build_root, archive_name)



def main():
    args = parseArguments()
    print(args)
    if args.clean:
        print 'Cleanig repository...'
        if os.path.isdir(breakpad_dir):
            print 'Deleting directory "%s"' % breakpad_dir
            try:
                shutil.rmtree(breakpad_dir)
            except OSError:
                pass

        cmd = ["git", "clean", "-dfx"]
        if not check_command(cmd, cwd=current_dir):
            print >> sys.stderr, "Clean failed"
            exit(1)

    if not initializeDepotTools(args.depot_tools):
        print >> sys.stderr, "Depot tools initialization failed for path \"%s\"." % args.depot_tools
        exit(1)

    if not os.path.exists(breakpad_dir):
        print "Initializing repository"
        if not initializeRepository():
            print >> sys.stderr, "Repositository initialization failed. Try running again with --clean."
            exit(1)
    elif args.update:
        print "Updating repository..."
        if not updateRepository():
            print >> sys.stderr, "Repository update failed. Try running again with --clean."
            exit(1)

    version = getRevision(os.path.join(breakpad_dir, 'src'))
    build(version)
    createPackage(breakpad_dir, version, args.platform)


main()
