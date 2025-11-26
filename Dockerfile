
# FROM ubuntu:20.04
# ARG DEBIAN_FRONTEND=noninteractive
# # ARG JAVA_HOME /usr/lib/jvm/java-8-openjdk-amd64

# ENV JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64
# ENV PATH=$JAVA_HOME/bin:$PATH

# RUN --mount=target=/var/lib/apt/lists,type=cache,sharing=locked \
#     --mount=target=/var/cache/apt,type=cache,sharing=locked \
#     apt update \
#     # Install runtime dependencies
#     && apt install -y openjdk-8-jdk ant unzip wget bc curl cpanminus git gradle graphviz maven subversion python vim autoconf automake bison build-essential clang cmake flex doxygen g++ git libffi-dev libncurses5-dev libsqlite3-dev make mcpp python sqlite zlib1g-dev libtool bash-completion openmpi-bin libpcl-dev python3-pip

# ENV JAVA_HOME /usr/lib/jvm/java-8-openjdk-amd64/

# RUN wget https://github.com/souffle-lang/souffle/archive/refs/tags/2.1.zip \
#     && unzip 2.1.zip \
#     && cd souffle-2.1 \
#     && cmake -S . -B build -DCMAKE_INSTALL_PREFIX=/usr \
#     && cmake --build build --target install



# COPY requirements.txt /tmp/requirements.txt

# RUN python3 -m pip install -r /tmp/requirements.txt

# RUN mkdir -p /amuse

# COPY . /amuse

# WORKDIR /amuse/

# RUN chmod u+x amuse

FROM ubuntu:22.04
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y \
        bison \
        build-essential \
        clang \
        cmake \
        doxygen \
        flex \
        g++ \
        git \
        libffi-dev \
        libncurses5-dev \
        libsqlite3-dev \
        make \
        mcpp \
        python3 \
        zlib1g-dev \
        wget \
        unzip \
        lsb-release \
        python3-pip \
        dpkg \
        openjdk-11-jdk


RUN wget -P /tmp https://github.com/souffle-lang/souffle/releases/download/2.2/x86_64-ubuntu-2104-souffle-2.2-Linux.deb \
    && dpkg -i /tmp/x86_64-ubuntu-2104-souffle-2.2-Linux.deb \
    && apt-get install -y -f \
    && rm /tmp/x86_64-ubuntu-2104-souffle-2.2-Linux.deb


# # Download and install Miniconda
# RUN wget --quiet https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda.sh && \
#     /bin/bash ~/miniconda.sh -b -p /opt/conda && \
#     rm ~/miniconda.sh && \
#     ln -s /opt/conda/etc/profile.d/conda.sh /etc/profile.d/conda.sh && \
#     echo ". /opt/conda/etc/profile.d/conda.sh" >> ~/.bashrc && \
#     echo "conda activate base" >> ~/.bashrc

# RUN conda update conda

# Download and install Miniconda
RUN wget --quiet https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda.sh && \
    /bin/bash ~/miniconda.sh -b -p /opt/conda && \
    rm ~/miniconda.sh

# Set environment variables for Conda
ENV PATH="/opt/conda/bin:$PATH"

# Initialize Conda
RUN /opt/conda/bin/conda init && \
    /bin/bash -c "source ~/.bashrc" && \
    conda update -n base -c defaults conda

RUN conda install -c potassco clingo

COPY requirements.txt /tmp/requirements.txt

WORKDIR /root

COPY . /root/amuse

ENV PYTHONPATH /root/amuse
