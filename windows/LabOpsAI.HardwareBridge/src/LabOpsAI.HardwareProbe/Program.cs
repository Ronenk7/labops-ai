using System.Globalization;
using LibreHardwareMonitor.Hardware;

const string separator =
    "============================================================";

var computer = new Computer
{
    IsCpuEnabled = true,
    IsGpuEnabled = true,
    IsMemoryEnabled = true,
    IsMotherboardEnabled = true,
    IsControllerEnabled = true,
    IsStorageEnabled = true,
    IsNetworkEnabled = false,
    IsPowerMonitorEnabled = true,
};

try
{
    computer.Open();
    computer.Accept(new UpdateVisitor());

    List<IHardware> hardwareDevices = EnumerateHardware(
        computer.Hardware
    ).ToList();

    Console.WriteLine(separator);
    Console.WriteLine("LabOps AI Focused Hardware Probe");
    Console.WriteLine($"Computer: {Environment.MachineName}");
    Console.WriteLine($"Collected: {DateTimeOffset.Now:O}");
    Console.WriteLine(separator);

    PrintCpu(hardwareDevices);
    PrintMemory(hardwareDevices);
    PrintNvidiaGpu(hardwareDevices);
    PrintMotherboard(hardwareDevices);
    PrintStorage(hardwareDevices);

    Console.WriteLine();
    Console.WriteLine(separator);
    Console.WriteLine("Probe completed.");
    Console.WriteLine(separator);
}
catch (Exception exception)
{
    Console.Error.WriteLine("Hardware collection failed.");
    Console.Error.WriteLine(
        $"{exception.GetType().Name}: {exception.Message}"
    );

    Environment.ExitCode = 1;
}
finally
{
    computer.Close();
}

static void PrintCpu(IEnumerable<IHardware> hardwareDevices)
{
    IHardware? cpu = hardwareDevices.FirstOrDefault(
        hardware => hardware.HardwareType == HardwareType.Cpu
    );

    PrintSection("CPU", cpu);

    if (cpu is null)
    {
        return;
    }

    PrintMetric(
        cpu,
        "Total Load",
        SensorType.Load,
        "CPU Total"
    );

    PrintMetric(
        cpu,
        "Maximum Core Load",
        SensorType.Load,
        "CPU Core Max"
    );

    PrintMetric(
        cpu,
        "Temperature",
        SensorType.Temperature,
        "Tctl/Tdie"
    );

    PrintMetric(
        cpu,
        "Package Power",
        SensorType.Power,
        "Package"
    );

    PrintMetric(
        cpu,
        "Average Clock",
        SensorType.Clock,
        "Cores (Average Effective)",
        "Cores (Average)"
    );
}

static void PrintMemory(IEnumerable<IHardware> hardwareDevices)
{
    IHardware? memory = hardwareDevices.FirstOrDefault(
        hardware =>
            hardware.HardwareType == HardwareType.Memory &&
            hardware.Name.Contains(
                "Total Memory",
                StringComparison.OrdinalIgnoreCase
            )
    );

    PrintSection("Physical Memory", memory);

    if (memory is null)
    {
        return;
    }

    PrintMetric(
        memory,
        "Usage",
        SensorType.Load,
        "Memory"
    );

    PrintMetric(
        memory,
        "Used",
        SensorType.Data,
        "Memory Used"
    );

    PrintMetric(
        memory,
        "Available",
        SensorType.Data,
        "Memory Available"
    );
}

static void PrintNvidiaGpu(
    IEnumerable<IHardware> hardwareDevices
)
{
    IHardware? gpu = hardwareDevices.FirstOrDefault(
        hardware =>
            hardware.HardwareType == HardwareType.GpuNvidia
    );

    PrintSection("NVIDIA GPU", gpu);

    if (gpu is null)
    {
        return;
    }

    PrintMetric(
        gpu,
        "Core Temperature",
        SensorType.Temperature,
        "GPU Core"
    );

    PrintMetric(
        gpu,
        "Memory Junction Temperature",
        SensorType.Temperature,
        "GPU Memory Junction"
    );

    PrintMetric(
        gpu,
        "Core Load",
        SensorType.Load,
        "GPU Core"
    );

    PrintMetric(
        gpu,
        "Memory Load",
        SensorType.Load,
        "GPU Memory"
    );

    PrintMetric(
        gpu,
        "Package Power",
        SensorType.Power,
        "GPU Package"
    );

    PrintMetric(
        gpu,
        "Core Clock",
        SensorType.Clock,
        "GPU Core"
    );

    PrintMetric(
        gpu,
        "Memory Clock",
        SensorType.Clock,
        "GPU Memory"
    );

    PrintMetric(
        gpu,
        "VRAM Used",
        SensorType.SmallData,
        "GPU Memory Used"
    );

    PrintMetric(
        gpu,
        "VRAM Total",
        SensorType.SmallData,
        "GPU Memory Total"
    );

    PrintMatchingSensors(
        gpu,
        "Fans",
        SensorType.Fan
    );
}

static void PrintMotherboard(
    IEnumerable<IHardware> hardwareDevices
)
{
    IHardware? motherboard = hardwareDevices.FirstOrDefault(
        hardware =>
            hardware.HardwareType == HardwareType.Motherboard
    );

    PrintSection("Motherboard", motherboard);

    if (motherboard is null)
    {
        return;
    }

    int printed = 0;

    printed += PrintMatchingSensors(
        motherboard,
        "Temperatures",
        SensorType.Temperature
    );

    printed += PrintMatchingSensors(
        motherboard,
        "Fans",
        SensorType.Fan
    );

    printed += PrintMatchingSensors(
        motherboard,
        "Voltages",
        SensorType.Voltage
    );

    if (printed == 0)
    {
        Console.WriteLine(
            "  Sensors: NOT AVAILABLE"
        );
    }
}

static void PrintStorage(
    IEnumerable<IHardware> hardwareDevices
)
{
    List<IHardware> storageDevices = hardwareDevices
        .Where(
            hardware =>
                hardware.HardwareType == HardwareType.Storage
        )
        .ToList();

    Console.WriteLine();
    Console.WriteLine("[Storage]");

    if (storageDevices.Count == 0)
    {
        Console.WriteLine("  Hardware: NOT DETECTED");
        return;
    }

    foreach (IHardware storage in storageDevices)
    {
        Console.WriteLine($"  Device: {storage.Name}");

        int printed = PrintMatchingSensors(
            storage,
            "Temperatures",
            SensorType.Temperature,
            indentation: "    "
        );

        if (printed == 0)
        {
            Console.WriteLine(
                "    Temperature: NOT AVAILABLE"
            );
        }
    }
}

static void PrintSection(
    string title,
    IHardware? hardware
)
{
    Console.WriteLine();
    Console.WriteLine($"[{title}]");

    if (hardware is null)
    {
        Console.WriteLine("  Hardware: NOT DETECTED");
        return;
    }

    Console.WriteLine($"  Device: {hardware.Name}");
    Console.WriteLine($"  ID: {hardware.Identifier}");
}

static void PrintMetric(
    IHardware hardware,
    string label,
    SensorType sensorType,
    params string[] sensorNames
)
{
    ISensor? sensor = EnumerateSensors(hardware)
        .FirstOrDefault(
            currentSensor =>
                currentSensor.SensorType == sensorType &&
                sensorNames.Any(
                    name => currentSensor.Name.Contains(
                        name,
                        StringComparison.OrdinalIgnoreCase
                    )
                )
        );

    if (
        sensor?.Value is not float value ||
        float.IsNaN(value) ||
        float.IsInfinity(value)
    )
    {
        Console.WriteLine($"  {label}: NOT AVAILABLE");
        return;
    }

    string suffix = GetUnit(sensor.SensorType);
    string warning = IsSuspicious(sensor.SensorType, value)
        ? " [SUSPICIOUS]"
        : string.Empty;

    Console.WriteLine(
        $"  {label}: " +
        $"{value.ToString("0.00", CultureInfo.InvariantCulture)}" +
        $"{suffix}{warning}"
    );
}

static int PrintMatchingSensors(
    IHardware hardware,
    string groupTitle,
    SensorType sensorType,
    string indentation = "  "
)
{
    List<ISensor> sensors = EnumerateSensors(hardware)
        .Where(
            sensor =>
                sensor.SensorType == sensorType &&
                sensor.Value is float value &&
                !float.IsNaN(value) &&
                !float.IsInfinity(value)
        )
        .OrderBy(
            sensor => sensor.Name,
            StringComparer.OrdinalIgnoreCase
        )
        .ToList();

    if (sensors.Count == 0)
    {
        return 0;
    }

    Console.WriteLine(
        $"{indentation}{groupTitle}:"
    );

    foreach (ISensor sensor in sensors)
    {
        float value = sensor.Value!.Value;
        string suffix = GetUnit(sensor.SensorType);
        string warning = IsSuspicious(
            sensor.SensorType,
            value
        )
            ? " [SUSPICIOUS]"
            : string.Empty;

        Console.WriteLine(
            $"{indentation}  {sensor.Name}: " +
            $"{value.ToString("0.00", CultureInfo.InvariantCulture)}" +
            $"{suffix}{warning}"
        );
    }

    return sensors.Count;
}

static IEnumerable<IHardware> EnumerateHardware(
    IEnumerable<IHardware> hardwareDevices
)
{
    foreach (IHardware hardware in hardwareDevices)
    {
        yield return hardware;

        foreach (
            IHardware subHardware in EnumerateHardware(
                hardware.SubHardware
            )
        )
        {
            yield return subHardware;
        }
    }
}

static IEnumerable<ISensor> EnumerateSensors(
    IHardware hardware
)
{
    foreach (ISensor sensor in hardware.Sensors)
    {
        yield return sensor;
    }

    foreach (IHardware subHardware in hardware.SubHardware)
    {
        foreach (
            ISensor sensor in EnumerateSensors(subHardware)
        )
        {
            yield return sensor;
        }
    }
}

static string GetUnit(SensorType sensorType)
{
    return sensorType switch
    {
        SensorType.Temperature => " °C",
        SensorType.Load => " %",
        SensorType.Power => " W",
        SensorType.Clock => " MHz",
        SensorType.Fan => " RPM",
        SensorType.Voltage => " V",
        SensorType.Data => " GB",
        SensorType.SmallData => " MB",
        _ => string.Empty,
    };
}

static bool IsSuspicious(
    SensorType sensorType,
    float value
)
{
    return sensorType switch
    {
        SensorType.Temperature => value <= 0 || value > 125,
        SensorType.Clock => value <= 0,
        SensorType.Power => value < 0,
        _ => false,
    };
}

internal sealed class UpdateVisitor : IVisitor
{
    public void VisitComputer(IComputer computer)
    {
        computer.Traverse(this);
    }

    public void VisitHardware(IHardware hardware)
    {
        hardware.Update();

        foreach (IHardware subHardware in hardware.SubHardware)
        {
            subHardware.Accept(this);
        }
    }

    public void VisitSensor(ISensor sensor)
    {
    }

    public void VisitParameter(IParameter parameter)
    {
    }
}
