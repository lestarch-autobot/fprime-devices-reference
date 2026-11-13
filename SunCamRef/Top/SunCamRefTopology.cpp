// ======================================================================
// \title  SunCamRefTopology.cpp
// \brief  topology instantiation code for SunCamRef
// ======================================================================
#include <SunCamRef/Top/SunCamRefTopologyAc.hpp>
#include <SunCamRef/Top/SunCamRefTopology.hpp>

#include <Fw/Logger/Logger.hpp>
#include <Fw/Types/MallocAllocator.hpp>
#include "Fw/Types/MemAllocator.hpp"

using namespace SunCamRef;

// Malloc allocator shared by the buffer managers (allocations happen at initialization only)
Fw::MallocAllocator mallocator;

namespace SunCamRef {
Fw::MemAllocator& memAllocator = mallocator;
}

// The Linux timer ticks at 10 Hz; rate group 1 divides by 10 (1 Hz), rate group 2 runs at the tick rate (10 Hz)
Svc::RateGroupDriver::DividerSet rateGroupDivisorsSet{{{10, 0}, {1, 0}}};

Svc::ActiveRateGroup::ContextArray rateGroup1Context(0);
Svc::ActiveRateGroup::ContextArray rateGroup2Context(0);

enum TopologyConstants {
    COMM_PRIORITY = 34,
    UART_PRIORITY = 33,
    // Camera line replies are ≤ 640 pixels + framing; one buffer per driver read
    UART_BUFFER_SIZE = 1024,
    UART_BUFFER_COUNT = 32,
    UART_BUFFER_MANAGER_ID = 400,
};

//! Pinned fprime-testing-harness (test-process contract §8): `git describe` of the harness checkout
static const char HARNESS_DESCRIBE[] = "fprime-testing-harness v0.1.20";

Svc::BufferManager::BufferBins uartBufferBins;

void configureTopology(const TopologyState& state) {
    rateGroupDriver.configure(rateGroupDivisorsSet);
    rateGroup1.configure(rateGroup1Context);
    rateGroup2.configure(rateGroup2Context);

    memset(&uartBufferBins, 0, sizeof(uartBufferBins));
    uartBufferBins.bins[0].bufferSize = UART_BUFFER_SIZE;
    uartBufferBins.bins[0].numBuffers = UART_BUFFER_COUNT;
    uartBufferManager.setup(UART_BUFFER_MANAGER_ID, 0, mallocator, uartBufferBins);

    // The test harness this deployment is paired with; the string lives in the image so the fth manifest
    // (which reads every pinned repository's describe string back from the image) accepts the build
    Fw::Logger::log("Paired test harness: %s\n", HARNESS_DESCRIBE);

    // Files (PrmDb.dat, DpCat) live in the working directory
    FileHandling::fileUplink.configure(".");
    FileHandling::fileDownlink.configure(".");
    FileHandling::prmDb.configureSandbox(".");

    if (state.uartDevice != nullptr) {
        // Camera link: 115200 8N1, no flow control (plan `scope`)
        const bool opened = uartDriver.open(state.uartDevice, Drv::PosixUartDriver::BAUD_115K,
                                            Drv::PosixUartDriver::NO_FLOW, Drv::PosixUartDriver::PARITY_NONE,
                                            UART_BUFFER_SIZE);
        if (!opened) {
            Fw::Logger::log("[ERROR] Failed to open UART device %s\n", state.uartDevice);
        }
    }
}

namespace SunCamRef {
void setupTopology(const TopologyState& state) {
    initComponents(state);
    setBaseIds();
    connectComponents();
    configComponents(state);
    if (state.hostname != nullptr && state.port != 0) {
        comDriver.configure(state.hostname, state.port);
    }
    configureTopology(state);
    regCommands();
    readParameters();
    loadParameters();
    startTasks(state);
    if (state.hostname != nullptr && state.port != 0) {
        Os::TaskString name("ReceiveTask");
        comDriver.start(name, COMM_PRIORITY, Default::STACK_SIZE);
    }
    if (state.uartDevice != nullptr) {
        uartDriver.start(UART_PRIORITY, Default::STACK_SIZE);
    }
}

void startRateGroups(const Fw::TimeInterval& interval) {
    linuxTimer.startTimer(interval);
}

void stopRateGroups() {
    linuxTimer.quit();
}

void teardownTopology(const TopologyState& state) {
    stopTasks(state);
    freeThreads(state);

    comDriver.stop();
    (void)comDriver.join();

    uartDriver.quitReadThread();
    (void)uartDriver.join();

    tearDownComponents(state);
    deinitComponents(state);
}
}  // namespace SunCamRef
