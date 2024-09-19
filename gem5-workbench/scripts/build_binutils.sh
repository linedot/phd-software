#!/bin/bash

# Build binutils for the given architecture

build_dir="unset"
out_dir="unset"
arch="unset"
version="unset"
sysroot="unset"

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
    -v|--version)
      version="$2"
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
check_argument sysroot "sysroot" "--sysroot"
((missing_arguments+=$?))
check_argument version "version" "--version"
((missing_arguments+=$?))


if [ 0 -lt $missing_arguments ]; then
    echo "Arguments missing, aborting"
    exit -1
fi


echo "Building binutils"
echo "Architecture     = ${arch}"
echo "Output directory = ${out_dir}"
echo "Build directory  = ${build_dir}"
echo "sysroot          = ${sysroot}"
echo "version          = ${version}"


mkdir -p ${build_dir}
cd ${build_dir}

gpg_dir=${build_dir}/gpg
mkdir -p ${gpg_dir}

# Download GNU's keyring and verify with that
gnu_keyring_file=gnu-keyring.gpg
if [ ! -e "${gnu_keyring_file}" ]; then
    echo "Downloading ${gnu_keyring_file}"
    curl -LO https://ftp.gnu.org/gnu/${gnu_keyring_file}
else
    echo "${gnu_keyring_file} already exists, using that file"
fi

archive_file=binutils-${version}.tar.xz
if [ ! -e "$archive_file" ]; then
    echo "Downloading ${archive_file}"
    curl -LO https://ftp.gnu.org/gnu/binutils/${archive_file}
else
    echo "$archive_file already exists, using that file"
fi

signature_file=binutils-${version}.tar.xz.sig
if [ ! -e "$signature_file" ]; then
    echo "Downloading ${signature_file}"
    curl -LO https://ftp.gnu.org/gnu/binutils/${signature_file}
else
    echo "$signature_file already exists, using that file"
fi

logfile="${build_dir}/binutils-gpg-verify.log"
echo "Verifying ${archive_file} with ${signature_file}. Log: ${logfile}"
gpg --homedir ${gpg_dir} --keyring $(pwd)/${gnu_keyring_file} --verify ${signature_file} ${archive_file} > $logfile 2>&1
if [ 0 -ne $? ]; then
    echo "Failed to verify ${archive_file} with ${signature_file}. Archive damaged/aborted download? Aborting"
    exit -1
fi


if [ ! -d "binutils-${version}" ]; then
    logfile="${build_dir}/binutils-untar.log"
    echo "Unpacking ${archive_file}. Log: ${logfile}"
    tar xJf ${archive_file} > ${logfile} 2>&1
else
    echo "Directory binutils-${version} exists, using that"
fi

logfile="${build_dir}/binutils-configure.log"
echo "Configuring binutils. Log: ${logfile}"
cd binutils-${version}
./configure --prefix="${out_dir}" \
            --build="$(uname -m)-linux-gnu" \
            --host="$(uname -m)-linux-gnu" \
            --target="${arch}-linux-gnu" \
            --disable-nls \
            --enable-deterministic-archives \
            --enable-gold \
            --enable-ld=default \
            --enable-multilib \
            --enable-plugins \
            --without-msgpack \
            --without-debuginfod \
            --with-gnu-as \
            --with-gnu-ld \
            --with-sysroot=$sysroot \
            --with-system-zlib > ${logfile} 2>&1
if [ 0 -ne $? ]; then
    echo "Failed to configure binutils"
    exit -1
fi
logfile="${build_dir}/binutils-build.log"
echo "Building binutils. Log: ${logfile}"
make MAKEINFO=true -j $NJOBS > ${logfile} 2>&1
if [ 0 -ne $? ]; then
    echo "Failed to build binutils"
    exit -1
fi
logfile="${build_dir}/binutils-install.log"
echo "Installing binutils. Log: ${logfile}"
make MAKEINFO=true -j $NJOBS install > ${logfile} 2>&1
if [ 0 -ne $? ]; then
    echo "Failed to install binutils"
    exit -1
fi

echo "Finished building and installing binutils ${version} into ${out_dir}. You can clean up ${build_dir} now"
