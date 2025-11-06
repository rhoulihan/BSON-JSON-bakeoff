#!/bin/bash
# Setup script for async-profiler
# Downloads and installs async-profiler for JVM flame graph generation

set -e

PROFILER_VERSION="3.0"
PROFILER_DIR="/opt/async-profiler"
TEMP_DIR="/tmp/async-profiler-setup"

echo "Setting up async-profiler v${PROFILER_VERSION}..."

# Check if already installed
if [ -f "${PROFILER_DIR}/lib/libasyncProfiler.so" ]; then
    echo "✓ async-profiler is already installed at ${PROFILER_DIR}"
    echo "Version: $(${PROFILER_DIR}/bin/asprof --version 2>&1 || echo 'unknown')"
    exit 0
fi

# Create temp directory
mkdir -p "${TEMP_DIR}"
cd "${TEMP_DIR}"

# Download async-profiler
echo "Downloading async-profiler ${PROFILER_VERSION}..."
curl -L "https://github.com/async-profiler/async-profiler/releases/download/v${PROFILER_VERSION}/async-profiler-${PROFILER_VERSION}-linux-x64.tar.gz" -o async-profiler.tar.gz

# Extract
echo "Extracting..."
tar -xzf async-profiler.tar.gz

# Install to /opt
echo "Installing to ${PROFILER_DIR}..."
sudo mkdir -p "${PROFILER_DIR}"
sudo cp -r async-profiler-${PROFILER_VERSION}-linux-x64/* "${PROFILER_DIR}/"
sudo chmod -R 755 "${PROFILER_DIR}"

# Create symlink in /usr/local/bin
echo "Creating symlink..."
sudo ln -sf "${PROFILER_DIR}/bin/asprof" /usr/local/bin/asprof

# Configure perf_event_paranoid for profiling
echo "Configuring system for profiling..."
CURRENT_PARANOID=$(cat /proc/sys/kernel/perf_event_paranoid)
if [ "$CURRENT_PARANOID" -gt 1 ]; then
    echo "Setting perf_event_paranoid to 1 (was ${CURRENT_PARANOID})..."
    echo 1 | sudo tee /proc/sys/kernel/perf_event_paranoid
    echo "Making change permanent..."
    echo "kernel.perf_event_paranoid=1" | sudo tee /etc/sysctl.d/99-perf.conf
fi

# Cleanup
cd -
rm -rf "${TEMP_DIR}"

echo ""
echo "✅ async-profiler installation complete!"
echo ""
echo "Installation location: ${PROFILER_DIR}"
echo "Library: ${PROFILER_DIR}/lib/libasyncProfiler.so"
echo "Command: asprof (symlinked to /usr/local/bin)"
echo ""
echo "Usage examples:"
echo "  # Profile Java application with CPU profiling"
echo "  java -agentpath:${PROFILER_DIR}/lib/libasyncProfiler.so=start,event=cpu,file=flamegraph.html -jar app.jar"
echo ""
echo "  # Or attach to running process"
echo "  asprof -d 30 -f flamegraph.html <pid>"
echo ""
