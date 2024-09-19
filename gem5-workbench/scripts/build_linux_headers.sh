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

echo $missing_arguments

if [ 0 -lt $missing_arguments ]; then
    echo "Arguments missing, aborting"
    exit -1
fi


echo "Building linux headers"
echo "Architecture     = ${arch}"
echo "Output directory = ${out_dir}"
echo "Build directory  = ${build_dir}"
echo "sysroot          = ${sysroot}"
echo "version          = ${version}"

kernel_arch=${arch}
if [[ "riscv64" == ${kernel_arch} ]]; then
    kernel_arch=riscv
elif [[ "aarch64" == ${kernel_arch} ]]; then
    kernel_arch=arm64
fi

mkdir -p ${build_dir}
cd ${build_dir}

gpg_dir=${build_dir}/gpg
mkdir -p ${gpg_dir}

archive_file=linux-${version}.tar.xz
if [ ! -e "$archive_file" ]; then
    echo "Downloading ${archive_file}"
    curl -LO https://www.kernel.org/pub/linux/kernel/v${version/.*/.x}/${archive_file}
else
    echo "$archive_file already exists, using that file"
fi

signature_file=linux-${version}.tar.sign
if [ ! -e "$signature_file" ]; then
    echo "Downloading ${signature_file}"
    curl -LO https://www.kernel.org/pub/linux/kernel/v${version/.*/.x}/${signature_file}
else
    echo "$signature_file already exists, using that file"
fi


# signature is for uncompressed archive
unxzed_archive_file=${archive_file/.xz/}
if [ ! -e "${unxzed_archive_file}" ]; then
    echo "un\"xz\"ing the tarball ${archive_file}"
    xz -k -d $archive_file
else
    echo "un\"xz\"ed tarball ${unxzed_archive_file} found, using that"
fi
archive_file=${unxzed_archive_file}

logfile="${build_dir}/linux-headers-gpg-verify.log"
echo "verifying ${archive_file} with ${signature_file}. Log: ${logfile}"
gpg --homedir ${gpg_dir} --keyserver hkps://keyserver.ubuntu.com --keyserver-options auto-key-retrieve --verify ${signature_file} ${archive_file} > $logfile 2>&1
if [ 0 -ne $? ]; then
    echo "Failed to verify ${archive_file} with ${signature_file}. Archive damaged/aborted download? Aborting"
    exit -1
fi

if [ ! -d "linux-${version}" ]; then
    logfile="${build_dir}/linux-untar.log"
    echo "Unpacking ${archive_file}. Log: ${logfile}"
    tar xf ${archive_file} > ${logfile} 2>&1
else
    echo "Directory linux-${version} exists, using that"
fi

logfile="${build_dir}/linux-headers-mrproper.log"
echo "cleaning up linux headers. Log: ${logfile}"
cd linux-${version}
make -j $(nproc) ARCH=${kernel_arch} mrproper 2>&1 >> $logfile
if [ 0 -ne $? ]; then
    echo "Failed to clean up linux headers"
    exit -1
fi

logfile="${build_dir}/linux-headers-headers_install.log"
echo "Installing linux headers. Log: ${logfile}"
make INSTALL_HDR_PATH="${sysroot}" ARCH=${kernel_arch} V=0 -j $(nproc) headers_install 2>&1 > $logfile
if [ 0 -ne $? ]; then
    echo "Failed to install linux headers"
    exit -1
fi

echo "Finished installing linux ${version} headers into ${out_dir}. You can clean up ${build_dir} now"
