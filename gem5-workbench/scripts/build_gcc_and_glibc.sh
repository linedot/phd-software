#!/bin/bash

# GCC and GLIBC have a bit of a dependency loop, so better build them together

build_dir="unset"
out_dir="unset"
arch="unset"
version_gcc="unset"
version_glibc="unset"
version_gmp="unset"
sysroot="unset"
patch_dir="unset"

positionals=()
while [[ $# -gt 0 ]]; do
  case $1 in
    -a|--architecture)
      arch="$2"
      shift
      shift
      ;;
    -o|--outputdirectory)
      out_dir="$2"
      shift
      shift
      ;;
    -b|--builddirectory)
      build_dir="$2"
      shift
      shift
      ;;
    -s|--sysroot)
      sysroot="$2"
      shift
      shift
      ;;
    -p|--patchdirectory)
      patch_dir="$2"
      shift
      shift
      ;;
    -v|--version_gcc)
      version_gcc="$2"
      shift
      shift
      ;;
    -V|--version_glibc)
      version_glibc="$2"
      shift
      shift
      ;;
    -G|--version_gmp)
      version_gmp="$2"
      shift
      shift
      ;;
    -*|--*)
      echo "Unknown option $1"
      exit 1
      ;;
    *)
      positionals+=("$1")
      shift
      ;;
  esac
done

set -- "${positionals[@]}" # restore positional parameters

missing_arguments=0;

check_argument() {
    if [[ "unset" == "${!1}" ]] || [ -z ${!1+x} ]; then
        echo "No $2 specified, specify $2 with $3"
        return 1
    fi
    return 0
}

check_argument arch "architecture" "--architecture"
((missing_arguments+=$?))
check_argument out_dir "output directory" "--outputdirectory"
((missing_arguments+=$?))
check_argument build_dir "build directory" "--builddirectory"
((missing_arguments+=$?))
check_argument patch_dir "patch directory" "--patchdirectory"
((missing_arguments+=$?))
check_argument sysroot "sysroot" "--sysroot"
((missing_arguments+=$?))
check_argument version_gcc "GCC version" "--version_gcc"
((missing_arguments+=$?))
check_argument version_glibc "GLIBC version" "--version_glibc"
((missing_arguments+=$?))
check_argument version_gmp "GMP version" "--version_gmp"
((missing_arguments+=$?))

echo $missing_arguments

if [ 0 -lt $missing_arguments ]; then
    echo "Arguments missing, aborting"
    exit -1
fi


echo "Building GCC and GLIBC"
echo "Architecture     = ${arch}"
echo "Output directory = ${out_dir}"
echo "Build directory  = ${build_dir}"
echo "Patch directory  = ${build_dir}"
echo "sysroot          = ${sysroot}"
echo "GCC version      = ${version_gcc}"
echo "GLIBC version    = ${version_glibc}"
echo "GMP version      = ${version_gmp}"


mkdir -p ${build_dir}
cd ${build_dir}

# Download GNU's keyring and verify with that
gnu_keyring_file=gnu-keyring.gpg
if [ ! -e "${gnu_keyring_file}" ]; then
    echo "Downloading ${gnu_keyring_file}"
    curl -LO https://ftp.gnu.org/gnu/${gnu_keyring_file}
else
    echo "${gnu_keyring_file} already exists, using that file"
fi

gcc_archive_file=gcc-${version_gcc}.tar.xz
if [ ! -e "$gcc_archive_file" ]; then
    echo "Downloading ${gcc_archive_file}"
    curl -LO https://ftp.gnu.org/gnu/gcc/${gcc_archive_file/.tar.xz/}/${gcc_archive_file}
else
    echo "$gcc_archive_file already exists, using that file"
fi

gcc_signature_file=gcc-${version_gcc}.tar.xz.sig
if [ ! -e "$gcc_signature_file" ]; then
    echo "Downloading ${gcc_signature_file}"
    curl -LO https://ftp.gnu.org/gnu/gcc/${gcc_signature_file/.tar.xz.sig/}/${gcc_signature_file}
else
    echo "$gcc_signature_file already exists, using that file"
fi

logfile="${build_dir}/gcc-gpg-verify.log"
echo "Verifying ${gcc_archive_file}. Log: ${logfile}"
gpg --keyring $(pwd)/${gnu_keyring_file} --verify ${gcc_signature_file} ${gcc_archive_file} > $logfile 2>&1
if [ 0 -ne $? ]; then
    echo "Failed to verify ${gcc_archive_file} with ${gcc_signature_file}. Archive damaged/aborted download? Aborting"
    exit -1
fi

glibc_archive_file=glibc-${version_glibc}.tar.xz
if [ ! -e "$glibc_archive_file" ]; then
    echo "Downloading ${glibc_archive_file}"
    curl -LO https://ftp.gnu.org/gnu/glibc/${glibc_archive_file}
else
    echo "$glibc_archive_file already exists, using that file"
fi

glibc_signature_file=glibc-${version_glibc}.tar.xz.sig
if [ ! -e "$glibc_signature_file" ]; then
    echo "Downloading ${glibc_signature_file}"
    curl -LO https://ftp.gnu.org/gnu/glibc/${glibc_signature_file}
else
    echo "$glibc_signature_file already exists, using that file"
fi

logfile="${build_dir}/glibc-gpg-verify.log"
echo "Verifying ${glibc_archive_file}. Log: ${logfile}"
gpg --keyring $(pwd)/${gnu_keyring_file} --verify ${glibc_signature_file} ${glibc_archive_file} > $logfile 2>&1
if [ 0 -ne $? ]; then
    echo "Failed to verify ${glibc_archive_file} with ${glibc_signature_file}. Archive damaged/aborted download? Aborting"
    exit -1
fi

gmp_archive_file=gmp-${version_gmp}.tar.xz
if [ ! -e "$gmp_archive_file" ]; then
    echo "Downloading ${gmp_archive_file}"
    curl -LO https://ftp.gnu.org/gnu/gmp/${gmp_archive_file}
else
    echo "$gmp_archive_file already exists, using that file"
fi

gmp_signature_file=gmp-${version_gmp}.tar.xz.sig
if [ ! -e "$gmp_signature_file" ]; then
    echo "Downloading ${gmp_signature_file}"
    curl -LO https://ftp.gnu.org/gnu/gmp/${gmp_signature_file}
else
    echo "$gmp_signature_file already exists, using that file"
fi

logfile="${build_dir}/gmp-gpg-verify.log"
echo "Verifying ${gmp_archive_file}. Log: ${logfile}"
gpg --keyring $(pwd)/${gnu_keyring_file} --verify ${gmp_signature_file} ${gmp_archive_file} > $logfile 2>&1
if [ 0 -ne $? ]; then
    echo "Failed to verify ${gmp_archive_file} with ${gmp_signature_file}. Archive damaged/aborted download? Aborting"
    exit -1
fi

if [ ! -d "gcc-${version_gcc}" ]; then
    logfile="${build_dir}/gcc-untar.log"
    echo "Unpacking ${gcc_archive_file}. Log: ${logfile}"
    tar xJf ${gcc_archive_file} > $logfile 2>&1
else
    echo "Directory gcc-${version_gcc} exists, using that"
fi

echo "Checking for GCC patches (filename must start with gcc-${version_gcc}):"
patches=($(ls -d ${patch_dir}/gcc-${version_gcc}*.patch 2>/dev/null))
if [ ${#patches[@]} -ne 0 ]; then
    logfile="${build_dir}/gcc-patching.log"
    echo "Applying GCC patches. Log: ${logfile}"
    for patch in "${patches[@]}"; do
        echo "Applying patch ${patch} to gcc-${version_gcc}"
        patch -d gcc-${version_gcc} -p1 < $patch > $logfile 2>&1
        if [ 0 -ne $? ]; then
            echo "Failed to apply patch ${patch}, aborting"
            exit -1
        fi
    done
else
    echo "No patches for GCC, proceeding as is"
fi

if [ ! -d "glibc-${version_glibc}" ]; then
    logfile="${build_dir}/glibc-untar.log"
    echo "Unpacking ${glibc_archive_file}" > $logfile 2>&1
    tar xJf ${glibc_archive_file}
else
    echo "Directory glibc-${version_glibc} exists, using that"
fi

echo "Checking for GLIBC patches (filename must start with glibc-${version_glibc}):"
patches=($(ls -d ${patch_dir}/glibc-${version_glibc}*.patch 2>/dev/null))
if [ ${#patches[@]} -ne 0 ]; then
    logfile="${build_dir}/glibc-patching.log"
    echo "Applying GLIBC patches. Log: ${logfile}"
    for patch in "${patches[@]}"; do
        echo "Applying patch ${patch} to glibc-${version_glibc}"
        patch -d glibc-${version_glibc} -p1 < $patch > $logfile 2>&1
        if [ 0 -ne $? ]; then
            echo "Failed to apply patch ${patch}, aborting"
            exit -1
        fi
    done
else
    echo "No patches for GLIBC, proceeding as is"
fi

if [ ! -d "gmp-${version_gmp}" ]; then
    logfile="${build_dir}/gmp-untar.log"
    echo "Unpacking ${gmp_archive_file}" > $logfile 2>&1
    tar xJf ${gmp_archive_file}
else
    echo "Directory gmp-${version_gmp} exists, using that"
fi

echo "Checking for GLIBC patches (filename must start with gmp-${version_gmp}):"
patches=($(ls -d ${patch_dir}/gmp-${version_gmp}*.patch 2>/dev/null))
if [ ${#patches[@]} -ne 0 ]; then
    logfile="${build_dir}/gmp-patching.log"
    echo "Applying GLIBC patches. Log: ${logfile}"
    for patch in "${patches[@]}"; do
        echo "Applying patch ${patch} to gmp-${version_gmp}"
        patch -d gmp-${version_gmp} -p1 < $patch > $logfile 2>&1
        if [ 0 -ne $? ]; then
            echo "Failed to apply patch ${patch}, aborting"
            exit -1
        fi
    done
else
    echo "No patches for GMP, proceeding as is"
fi


#Check binutils
bu_bins=($(ls ${out_dir}/bin/${arch}-linux-gnu-*))
if [ ${#bu_bins[@]} -eq 0 ]; then
    echo "Binutils are missing! Aborting"
    exit -1
fi

if [ -d gmp-build ]; then
    echo "Removing old gmp-build directory"
    rm -rf gmp-build
fi
mkdir gmp-build
cd gmp-build
logfile="${build_dir}/gmp-configure.log"
echo "Configuring GMP. Log: ${logfile}"
export CC="gcc"
export CXX="g++"
oldpath=$PATH
export PATH="${build_dir}/bin:${out_dir}/bin/:$PATH"
../gmp-${version_gmp}/configure --prefix="${out_dir}" \
                                --disable-multilib \
                                --disable-nls \
                                --disable-shared \
                                --disable-decimal-float \
                                --disable-threads \
                                --disable-libatomic \
                                --disable-libgomp \
                                --disable-libquadmath \
                                --disable-libssp \
                                --disable-libvtv \
                                --disable-libstdcxx > $logfile 2>&1
if [ 0 -ne $? ]; then
    echo "Failed to configure GMP"
    exit -1
fi
logfile="${build_dir}/gmp-build.log"
echo "Building GMP. Log: ${logfile}"
make -j $(nproc) > $logfile 2>&1
if [ 0 -ne $? ]; then
    echo "Failed to build GMP"
    exit -1
fi
logfile="${build_dir}/gmp-install.log"
echo "Installing GMP. Log: ${logfile}"
make -j $(nproc) install > $logfile 2>&1
if [ 0 -ne $? ]; then
    echo "Failed to install GMP"
    exit -1
fi
export PATH=$oldpath
cd ..


cd gcc-${version_gcc}
logfile="${build_dir}/gcc-download_prerequisites.log"
echo "Downloading GCC prerequisites. Log: ${logfile}"
./contrib/download_prerequisites > $logfile 2>&1
cd ..
if [ -d gcc-build ]; then
    echo "Removing old gcc-build directory"
    rm -rf gcc-build
fi
mkdir gcc-build
cd gcc-build
logfile="${build_dir}/gcc-stage1-configure.log"
echo "Configuring stage 1 GCC. Log: ${logfile}"
export CC="gcc"
export CXX="g++"
oldpath=$PATH
export PATH="${build_dir}/stage1-gcc/bin:${out_dir}/bin/:$PATH"
../gcc-${version_gcc}/configure --prefix="${build_dir}/stage1-gcc" \
                                --build="$(uname -m)-linux-gnu" \
                                --host="$(uname -m)-linux-gnu" \
                                --target="${arch}-linux-gnu" \
                                --with-local-prefix=/usr \
                                --with-sysroot=$sysroot \
                                --with-build-sysroot=$sysroot \
                                --with-native-system-header-dir=/include \
                                --with-as=$(which ${arch}-linux-gnu-as) \
                                --with-ld=$(which ${arch}-linux-gnu-ld) \
                                --with-gnu-as \
                                --with-gnu-ld \
                                --disable-multilib \
                                --without-headers \
                                --with-newlib \
                                --with-gmp=${out_dir} \
                                --enable-languages=c,c++ \
                                --disable-nls \
                                --disable-shared \
                                --disable-decimal-float \
                                --disable-threads \
                                --disable-libatomic \
                                --disable-libgomp \
                                --disable-libquadmath \
                                --disable-libssp \
                                --disable-libvtv \
                                --disable-libstdcxx > $logfile 2>&1
if [ 0 -ne $? ]; then
    echo "Failed to configure stage 1 GCC"
    exit -1
fi
logfile="${build_dir}/gcc-stage1-build.log"
echo "Building stage 1 GCC. Log: ${logfile}"
make -j $(nproc) all-gcc all-target-libgcc > $logfile 2>&1
if [ 0 -ne $? ]; then
    echo "Failed to build stage 1 GCC"
    exit -1
fi
logfile="${build_dir}/gcc-stage1-install.log"
echo "Installing stage 1 GCC. Log: ${logfile}"
make -j $(nproc) install-gcc install-target-libgcc > $logfile 2>&1
if [ 0 -ne $? ]; then
    echo "Failed to install stage 1 GCC"
    exit -1
fi
export PATH=$oldpath
cd ..

if [ -d glibc-build ]; then
    echo "Removing old glibc-build directory"
    rm -rf glibc-build
fi
mkdir glibc-build
cd glibc-build
logfile="${build_dir}/glibc-configure.log"
echo "Configuring GLIBC. Log: ${logfile}"
export CC="${build_dir}/stage1-gcc/bin/${arch}-linux-gnu-gcc"
export CXX="${build_dir}/stage1-gcc/bin/${arch}-linux-gnu-g++"
oldpath=$PATH
export PATH="${out_dir}/${arch}-linux-gnu/bin/:$PATH"
../glibc-${version_glibc}/configure --prefix=/usr \
                                    --target="${arch}-linux-gnu" \
                                    --with-glibc-version=${version_glibc} \
                                    --host=${arch}-linux-gnu \
                                    --libdir=/usr/lib \
                                    --libexecdir=/usr/lib \
                                    --with-headers=${sysroot}/include \
                                    --enable-kernel=4.19.288 \
                                    --enable-add-ons \
                                    --enable-bind-now \
                                    --disable-profile \
                                    --enable-stackguard-randomization \
                                    --enable-lock-elision \
                                    --disable-werror > $logfile 2>&1
if [ 0 -ne $? ]; then
    echo "Failed to configure GLIBC"
    exit -1
fi
logfile="${build_dir}/glibc-build.log"
echo "Building GLIBC. Log: ${logfile}"
make -j $(nproc) > $logfile 2>&1
if [ 0 -ne $? ]; then
    echo "Failed to build GLIBC"
    exit -1
fi
logfile="${build_dir}/glibc-install.log"
echo "Installing GLIBC. Log: ${logfile}"
make -j $(nproc) install_root=${sysroot} install > $logfile 2>&1
if [ 0 -ne $? ]; then
    echo "Failed to install GLIBC"
    exit -1
fi
cd ..
export PATH=$oldpath

logfile="${build_dir}/gcc-stage2-configure.log"
echo "Configuring stage 2 (final) GCC. Log: ${logfile}"
cd gcc-build && rm -rf *
export CC="gcc"
export CXX="g++"
../gcc-${version_gcc}/configure --prefix="${out_dir}" \
                                --build="$(uname -m)-linux-gnu" \
                                --host="$(uname -m)-linux-gnu" \
                                --target="${arch}-linux-gnu" \
                                --disable-multilib \
                                --program-prefix=${arch}-linux-gnu- \
                                --enable-languages=c,c++,fortran \
                                --with-local-prefix=/usr \
                                --with-sysroot=$sysroot \
                                --with-build-sysroot=$sysroot \
                                --with-native-system-header-dir=/include \
                                --with-system-zlib \
                                --includedir=${sysroot}/usr/include \
                                --includedir=${sysroot}/include \
                                --includedir=${out_dir}/include \
                                --libdir=${out_dir}/lib \
                                --libexecdir=${out_dir}/lib \
                                --with-system-zlib \
                                --with-isl \
                                --with-gmp=${out_dir} \
                                --with-linker-hash-style=gnu \
                                --disable-nls \
                                --disable-libunwind-exceptions \
                                --disable-libstdcxx-pch \
                                --disable-libssp \
                                --disable-werror \
                                --enable-shared \
                                --enable-threads=posix \
                                --enable-__cxa_atexit \
                                --enable-clocale=gnu \
                                --enable-gnu-unique-object \
                                --enable-linker-build-id \
                                --enable-lto \
                                --enable-plugin \
                                --enable-install-libiberty \
                                --enable-gnu-indirect-function \
                                --enable-default-pie \
                                --enable-checking=release > $logfile 2>&1


if [ 0 -ne $? ]; then
    echo "Failed to configure stage 2 (final) GCC"
    exit -1
fi
logfile="${build_dir}/gcc-stage2-build.log"
echo "Building stage 2 (final) GCC. Log: ${logfile}"
CC="gcc" && \
CXX="g++" && \
make -j $(nproc) > $logfile 2>&1
if [ 0 -ne $? ]; then
    echo "Failed to build stage 2 (final) GCC"
    exit -1
fi
logfile="${build_dir}/gcc-stage2-install.log"
echo "Installing stage 2 (final) GCC. Log: ${logfile}"
make -j $(nproc) install-gcc install-target-{libgcc,libstdc++-v3,libgomp,libgfortran,libquadmath,libatomic} > $logfile 2>&1
if [ 0 -ne $? ]; then
    echo "Failed to install stage 2 (final) GCC"
    exit -1
fi
cd ..


echo "Finished building and installing GCC ${version_gcc} and GLIBC ${version_glibc} into"
echo "${out_dir}. You can clean up ${build_dir} now"
