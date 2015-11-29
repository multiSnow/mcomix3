#!/bin/bash

# set -x

# Trap errors
trap 'exit $?' ERR
# Inherit trap in subshells, functions.
set -E

# Helper to avoid errors trap.
notrap()
{
  "$@" || true
}

info()
{
  echo "[34m$@[0m"
}

err()
{
  echo 1>&2 "[31m$@[0m"
}

win32dir="$(realpath "$(dirname "$0")")"
mcomixdir="$(realpath "$win32dir/..")"
winedir="$win32dir/.wine"
tmpdir="$winedir/tmp"
distdir="$win32dir/.dist"
installed="$winedir/installed"
programfiles="$winedir/drive_c/Program Files"

export WINEARCH='win32' WINEPREFIX="$winedir" WINEDEBUG="-all"
unset PYTHONPATH
# Make sure GTK environment variables don't spill over to the Wine environment.
unset \
  GDK_BACKEND \
  GDK_NATIVE_WINDOWS \
  GDK_PIXBUF_MODULE_FILE \
  GDK_RENDERING \
  GTK2_RC_FILES \
  GTK3_MODULES \
  GTK_DATA_PREFIX \
  GTK_EXE_PREFIX \
  GTK_IM_MODULE \
  GTK_IM_MODULE_FILE \
  GTK_MODULES \
  GTK_PATH \
  GTK_THEME \

add_to_wine_path()
{
  winepath="$(echo -n "$1" | sed 's,[^/]$,&/,;s,/,\\\\\\\\,g')"
  cat >"$winedir/path.reg" <<EOF
REGEDIT4

[HKEY_LOCAL_MACHINE\System\CurrentControlSet\Control\Session Manager\Environment]
EOF
  sed -n "/^\"PATH\"=str(2):\"/{h;/[\";]${winepath}[\";]/"'!'"{s/:\"/&${winepath};/};h;p;Q0};\$Q1" "$winedir/system.reg" >>"$winedir/path.reg"
  winecmd regedit "$winedir/path.reg"
}

winecmd()
{
  # Avoid errors trap.
  if "$@"
  then
    code=$?
  else
    code=$?
  fi
  wineserver -w
  return $code
}

winetricks()
{
  info "winetricks $@"
  env WINETRICKS_OPT_SHAREDPREFIX=1 winetricks "$@"
}

install()
{
  name="$1"
  src="$2"
  crc="$3"
  file="$(basename "$src")"
  dst="$distdir/$file"

  if grep -qxF "$file" "$installed"
  then
    return 0
  fi

  if [ ! -r "$dst" ]
  then
    info "downloading $name"
    wget --quiet --show-progress --continue -O "$dst" "$src"
  fi

  if ! sha1sum --quiet --check --status - <<<"$crc $dst"
  then
    err "SHA1 does not match: calculated $(sha1sum "$dst" | cut -d' ' -f1) (instead of $crc)"
    notrap rm -vf "$dst"
    return 1
  fi

  info "installing $name"

  shift 3
  if [ 0 -eq $# ]
  then
    return 1
  fi

  cmd="$1"
  shift
  "$cmd" "$file" "$@"

  echo "$file" >>"$installed"
}

install_7zip()
{
  file="$1"
  src="$distdir/$file"

  install_msi "$file" /q
  add_to_wine_path 'C:/Program Files/7-Zip'
}

install_unzip()
{
  file="$1"
  src="$distdir/$file"

  rm -rf "$programfiles/unzip"
  mkdir "$programfiles/unzip"
  (
    cd "$programfiles/unzip"
    winecmd wine "$src"
  )
  add_to_wine_path "C:/Program Files/unzip"
}

build_distribute()
{
  cp "$winedir/drive_c/Python27/Lib/site-packages/setuptools/cli-32.exe" setuptools/
  winecmd wine python.exe setup.py --quiet install
}

install_exe()
{
  file="$1"
  src="$distdir/$file"
  shift
  options=("$@")

  winecmd wine "$src" "${options[@]}"
}

install_msi()
{
  file="$1"
  src="$distdir/$file"
  shift
  options=("$@")

  winecmd msiexec /i "$src" "${options[@]}"
}

install_archive()
{
  file="$1"
  dstdir="$2"
  format="$3"

  cmd=(aunpack --save-outdir="$file.dir")
  if [[ -n "$format" ]]
  then
    cmd+=(--format="$format")
  fi
  cmd+=("$distdir/$file")

  rm -rf "$programfiles/$dstdir"
  (
    cd "$tmpdir"
    cat /dev/null >"$file.dir"
    "${cmd[@]}" >/dev/null
  )
  srcdir="$tmpdir/$(cat "$tmpdir/$file.dir")"
  mv -v "$srcdir" "$programfiles/$dstdir"
  add_to_wine_path "C:/Program Files/$dstdir"
}

install_python_source()
{
  file="$1"
  build="$2"

  case "$file" in
    *.zip)
      dir="${file%.zip}"
      ;;
    *.tar.gz)
      dir="${file%.tar.gz}"
      ;;
    *)
      return 1
      ;;
  esac

  rm -rf "$tmpdir/$dir"

  aunpack --quiet --extract-to "$tmpdir" "$distdir/$file"

  (
    cd "$tmpdir/$dir"
    if [ -z "$build" ]
    then
      winecmd wine python.exe setup.py --quiet install
    else
      "$build"
    fi
  )

  rm -rf "$tmpdir/$dir"

  return 0
}

install_mimetypes()
{
  file="$1"
  src="$distdir/$file"
  dst="$winedir/drive_c/Python27/Lib/$file"

  cp -v "$src" "$dst"
  winecmd wine python.exe -m py_compile "$dst"
}

install_pygobject()
{
  file="$1"
  shift
  srcdir="$tmpdir/${file%.exe}"
  dstdir="$winedir/drive_c/Python27/Lib/site-packages"

  rm -rf "$srcdir"
  aunpack --extract-to="$srcdir" --format=7z "$distdir/$file" >/dev/null
  python2 "$win32dir/pygi-aio-installer.py" "$srcdir" "$dstdir" "$@"
  rm -rf "$srcdir"
}

install_pygtk()
{
  file="$1"
  srcdir="$tmpdir/${file%.7z}"
  dstdir="$winedir/drive_c/Python27/Lib"

  rm -rf "$srcdir"
  aunpack --extract-to="$srcdir" "$distdir/$file" >/dev/null
  cp -auv "$srcdir/py27-32"/* "$dstdir/"
  rm -rf "$srcdir"
}

install_mcomix()
{
  file="$1"
  version="$2"

  echo install_mcomix "$version"
  aunpack --extract-to="$programfiles" "$distdir/$file" >/dev/null
}

helper_setup()
{
  winecmd wineboot --init
  mkdir -p "$distdir" "$tmpdir"
  touch "$installed"
  # Bare minimum for running MComix.
  install 'Python' 'https://www.python.org/ftp/python/2.7.10/python-2.7.10.msi' 9e62f37407e6964ee0374b32869b7b4ab050d12a install_msi /q
  install 'PyGObject for Windows' 'http://downloads.sourceforge.net/project/pygobjectwin32/pygi-aio-3.18.2_rev3-setup.exe' f54d00b245da423465081c01df1347282c289049 install_pygobject GTK
  install 'PyGObject for Windows: legacy PyGTK' 'http://downloads.sourceforge.net/project/pygobjectwin32/legacy_pygtk-2.24.0_gtk-2.24.28+themes_py27_win32_win64.7z' 295fe473cea9eeeb20a75b8b0c6b2a7215347566 install_pygtk
  install 'Pillow' 'https://pypi.python.org/packages/2.7/P/Pillow/Pillow-2.8.1.win32-py2.7.exe' 9221e1695cc3b510ceb4748035fffc03c823f9e0 install_exe
  # Better support for password protected zip files.
  install 'Python: czipfile' 'https://pypi.python.org/packages/2.7/c/czipfile/czipfile-1.0.0.win32-py2.7.exe' 8478c1d659821259c1140cd8600d61a2fa13128f install_exe
  # Support for RAR files.
  install 'UnRAR DLL' 'http://www.rarlab.com/rar/UnRARDLL.exe' 9242cd1b756c1428f168db74cf99000afbbff861 install_archive UnrarDLL rar
  # Support for PDF files.
  install 'MuPDF' 'http://mupdf.com/downloads/archive/mupdf-1.8-windows.zip' 27683c9186eab0bd53674e959c102bc88c384017 install_archive MuPDF
  # Support for 7z files.
  install '7zip' 'http://7-zip.org/a/7z938.msi' 5f66856e4bacd1801054b6cd3c40d34d0dfc4609 install_7zip
  # Additional extractors for testing.
  install 'UnrarDLL executable' 'http://www.rarlab.com/rar/unrarw32.exe' bff8bf0c385113daee39abb819323275db08adf1 install_archive Unrar rar
  install 'UnZIP executable' 'ftp://ftp.info-zip.org/pub/infozip/win32/unz600xn.exe' 5ae7a23e7abf2c5ca44cefb0d6bf6248e6563db1 install_archive unzip zip
  # Install PyInstaller and dependencies.
  install 'PyInstaller dependency: Python for Windows Extensions' 'http://downloads.sourceforge.net/project/pywin32/pywin32/Build 219/pywin32-219.win32-py2.7.exe' 8bc39008383c646bed01942584117113ddaefe6b install_exe
  install 'PyInstaller dependency: setuptools' 'https://pypi.python.org/packages/source/s/setuptools/setuptools-14.3.1.zip' fb16eea8e9ddb5a973e98362aabb9675c8ec63ee install_python_source
  install 'PyInstaller dependency: distribute' 'https://pypi.python.org/packages/source/d/distribute/distribute-0.7.3.zip' 297bd0725027ca39dcb35fa00327bc35b2f2c5e3 install_python_source build_distribute
  install 'PyInstaller' 'https://pypi.python.org/packages/source/P/PyInstaller/PyInstaller-2.1.tar.gz' 530e0496087ea955ebed6f11b0172c50c73952af install_python_source
  # Install pytest and dependencies.
  install 'PyTest dependency: colorama' 'https://pypi.python.org/packages/source/c/colorama/colorama-0.3.3.tar.gz' a8ee91adf4644bbdccfc73ead88f4cd0df7e3552 install_python_source
  install 'PyTest dependency: py' 'https://pypi.python.org/packages/source/p/py/py-1.4.26.tar.gz' 5d9aaa67c1da2ded5f978aa13e03dfe780771fea install_python_source
  install 'PyTest' 'https://pypi.python.org/packages/source/p/pytest/pytest-2.7.0.tar.gz' 297b27dc5a77ec3a22bb2bee1dfa178ec162d9e4 install_python_source
  # Install last 2 releases of MComix for easier regression testing.
  install 'MComix 1.00' http://downloads.sourceforge.net/project/mcomix/MComix-1.00/mcomix-1.00.win32.all-in-one.zip 4002cf441abd4fb616bb409407d86861b1224fca install_mcomix 1.00
  install 'MComix 1.01' http://downloads.sourceforge.net/project/mcomix/MComix-1.01/mcomix-1.01-2.win32.all-in-one.zip 44b24db3cec4fd66c2df05d25d70f47125da2100 install_mcomix 1.01
  winetricks corefonts
  true
}

helper_dist()
{(
  manifest="$mcomixdir/build/manifest"

  cd "$mcomixdir"
  rm -rf build dist
  mkdir build
  version="$(python2 -c 'from mcomix.constants import VERSION; print VERSION')"

  # Create manifest ourselves (see setup.py...).
  if [ -d "$mcomixdir/.git" ]
  then
    git -C "$mcomixdir" ls-files >"$manifest"
  elif [ -d "$mcomixdir/.svn" ]
  then
    svn list -R "$mcomixdir" >"$manifest"
  else
    err "no supported VCS"
    return 1
  fi

  export SETUPTOOLS_MANIFEST="$manifest"

  # Build egg.
  info "building egg"
  winecmd wine python.exe setup.py --quiet bdist_egg
  test -r "dist/mcomix-$version-py2.7.egg"

  # Create install data.
  info "running pyinstaller"
  echo 'from mcomix.run import run; run()' >build/launcher.py
  winecmd wine pyinstaller.exe \
    --log-level WARN \
    --paths "dist/mcomix-$version-py2.7.egg" \
    --icon mcomix/images/mcomix.ico \
    --additional-hooks-dir win32 \
    --name MComix \
    --noconfirm \
    --windowed \
    build/launcher.py
  mv -v dist/MComix "dist/MComix-$version"

  # Pack archive.
  info "packing archive"
  (
    cd dist
    zip -9 -r "mcomix-$version.win32.all-in-one.zip" "MComix-$version"
  )
)}

helper_dist_setup()
{(
  winedir="$win32dir/.wine-dist"
  tmpdir="$winedir/tmp"
  programfiles="$winedir/drive_c/Program Files"

  export WINEARCH='win32' WINEPREFIX="$winedir"

  cd "$mcomixdir"
  rm -rf "$winedir"
  winecmd wineboot --init
  mkdir -p "$distdir" "$tmpdir"
  version="$(python2 -c 'from mcomix.constants import VERSION; print VERSION')"
  cp "$mcomixdir/dist/mcomix-$version.win32.all-in-one.zip" "$distdir/"
  install_archive "mcomix-$version.win32.all-in-one.zip" MComix
  winetricks corefonts
)}

helper_dist_mcomix()
{(
  winedir="$win32dir/.wine-dist"
  export WINEARCH='win32' WINEPREFIX="$winedir"
  winecmd wine MComix.exe "$@"
)}

helper_dist_shell()
{(
  winedir="$win32dir/.wine-dist"
  export WINEARCH='win32' WINEPREFIX="$winedir"
  "$SHELL" "$@"
)}

helper_dist_test()
{
  helper_dist
  helper_dist_setup
  helper_dist_mcomix "$@"
}

helper_mcomix()
{
  execmd=(python.exe "$(winepath -w "$mcomixdir/mcomixstarter.py")")
  exeargs=()
  for arg in "$@"
  do
    case "$arg" in
      -src)
        ;;
      -[0-9]*)
        execmd=("$(winepath -w "$programfiles/MComix$arg/MComix.exe")" )
        ;;
      *)
        exeargs+=("$arg")
        ;;
    esac
  done
  winecmd wine "${execmd[@]}" "${exeargs[@]}"
}

helper_wine()
{
  winecmd wine "$@"
}

helper_python()
{
  winecmd wine python.exe "$@"
}

helper_test()
{
  helper_python test/run.py "$@"
}

helper_shell()
{
  "$SHELL" "$@"
}

helper_help()
{
  cat <<EOF

Usage: $(basename "$0") [command] [arguments...]

General commands:

  help                    Show this help.
  setup                   Initialize Wine prefix for development.
                          Note: the prefix is created in win32/.wine,
                          and contains everything needed to develop,
                          run, and package MComix Windows version.

Commands using the Wine prefix created by 'setup':

  mcomix [-ver] [args...] Run Windows version of MComix.
                          -ver handling:
                            - run from source with -src or when unspecifed
                            - -x.xx to run installed release version x.xx
  wine [args...]          Run 'wine' with the specified arguments.
  python [args...]        Run 'python' with the specified arguments.
  test [args...]          Run Windows version of MComix test suite.
  shell [args...]         Run \$SHELL with the specified arguments.
  dist                    Create Windows distribution from MComix source.
  dist-setup              Create Wine prefix for testing the distribution.
                          Note: depend on the result of the 'dist' command,
                          the prefix is created in win32/.wine-dist, and
                          deleted before being recreated if already existing.
  dist-test [args...]     Equivalent to using 'dist', followed by 'dist-setup'
                          and 'dist-mcomix' with the specified arguments.

Commands using the Wine prefix created by 'dist-setup':

  dist-mcomix [args...]   Run Windows distribution version of MComix.
  dist-shell [args...]    Run \$SHELL with the specified arguments.

EOF
}

helper="$(echo -n "$1" | tr - _)"
shift
helper_"$helper" "$@"

