# dk001/skp-converter
# Headless SketchUp .skp -> .dae converter using SketchUp's LayOut CLI
# 
# Build:
#   docker build -t dk001/skp-converter .
#
# Use:
#   docker run --rm -v $(pwd):/data dk001/skp-converter model.skp
#   # Outputs model.dae in the same directory
#
# Or via extract.py (automatic):
#   python extract.py --input model.skp
#   (skp.py detects Docker and calls this image automatically)

FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV SKP_CONVERTER_VERSION=1.0.0

# System deps
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    wget \
    curl \
    unzip \
    libglib2.0-0 \
    libgl1-mesa-glx \
    libx11-6 \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Python deps
RUN pip3 install --no-cache-dir \
    trimesh[easy]>=4.0.0 \
    numpy>=1.24.0 \
    lxml>=4.9.0 \
    ezdxf>=1.1.0

WORKDIR /app

# Copy the converter script
COPY docker/skp_convert.py /app/skp_convert.py

ENTRYPOINT ["python3", "/app/skp_convert.py"]
