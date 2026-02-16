# Installing OpenFOAM-v2512 on Ubuntu Linux

This guide provides step-by-step instructions for installing OpenFOAM-v2512 on an Ubuntu Linux system.


## Installation Directories

The default root directory for this installation is `/opt/OpenFOAM`. If you prefer a different location, please replace `/opt/OpenFOAM` with your chosen path throughout the process.

The specific installation paths are as follows:

| Component | Directory Path |
| --- | --- |
| OpenFOAM-v2512 | /opt/OpenFOAM/OpenFOAM-v2512 |
| ThirdParty-v2512 | /opt/OpenFOAM/ThirdParty-v2512 |

## Prerequisites

To install the necessary build dependencies, switch to the root user (`sudo su -`) and run the following commands:

```
apt-get -y update
apt -y upgrade
apt-get install -y build-essential flex zlib1g-dev libgmp-dev libmpfr-dev texinfo cmake
```

## Install OpenMPI

OpenMPI is required for parallel computing. This guide covers the installation of OpenMPI version 4.0.5; instructions for other MPI distributions are not included.

Run the following to download, compile, and install OpenMPI to `/opt/openmpi-4.0.5`:

```
wget https://download.open-mpi.org/release/open-mpi/v4.0/openmpi-4.0.5.tar.gz
tar zxf openmpi-4.0.5.tar.gz
rm openmpi-4.0.5.tar.gz
cd openmpi-4.0.5
./configure --prefix=/opt/openmpi-4.0.5
make -j all
make install
echo 'export PATH=$PATH:/opt/openmpi-4.0.5/bin' >> /etc/bash.bashrc
```

## Download and Prepare Source Code

```
wget https://dl.openfoam.com/source/v2512/OpenFOAM-v2512.tgz
wget https://dl.openfoam.com/source/v2512/ThirdParty-v2512.tar.gz
tar zxf OpenFOAM-v2512.tgz
tar zxf ThirdParty-v2512.tar.gz
mkdir -p /opt/OpenFOAM
mv OpenFOAM-v2512 /opt/OpenFOAM
mv ThirdParty-v2512 /opt/OpenFOAM
```

## Configure the Environment

You must update the project directory path within the OpenFOAM environment settings. Open the `bashrc` file:

```
vi /opt/OpenFOAM/OpenFOAM-v2512/etc/bashrc
```

Locate and set the `projectDir` variable as follows:

```
projectDir="/opt/OpenFOAM/OpenFOAM-$WM_PROJECT_VERSION"
```

## Compilation

After configuring the environment, you can begin the compilation process:

```
source /opt/OpenFOAM/OpenFOAM-v2512/etc/bashrc
cd /opt/OpenFOAM/OpenFOAM-v2512
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$WM_THIRD_PARTY_DIR/platforms/linux64Gcc/fftw-3.3.10/lib
./Allwmake -j
```

## Finalize Installation

To ensure the OpenFOAM environment variables are automatically loaded whenever you open a new terminal, add the source command to your global `bashrc`:

```
echo 'source /opt/OpenFOAM/OpenFOAM-v2512/etc/bashrc' >> /etc/bash.bashrc
```
