package TemperatureMonitoring {
    private import ScalarValues::Real;

    port def TemperatureInput { in attribute temperature : Real; }
    port def TemperaturePort {
        out attribute temperature : Real;
    }
    part def Sensor {
        port temperatureOut : TemperaturePort;
    }
    action def ReadTemperature {
        in attribute sample : Real;
        out attribute reading : Real;
        bind reading = sample;
    }
    part def Controller {
        port temperatureIn : TemperatureInput;
        perform action readTemperature : ReadTemperature;
        bind readTemperature.sample = temperatureIn.temperature;
    }
    interface def TemperatureTransfer {
        end source : TemperaturePort;
        end target : TemperatureInput;
        flow source.temperature to target.temperature;
    }
    part def MonitoringSystem {
        part sensor : Sensor;
        part controller : Controller;
        interface temperatureLink : TemperatureTransfer
            connect sensor.temperatureOut to controller.temperatureIn;
    }
    part monitoringSystem : MonitoringSystem;
}
