import React, { useState, useEffect } from "react";
import "./esim_devices.css";

const EsimDevices = () => {
    const [deviceData, setDeviceData] = useState([]);
    const [openCategory, setOpenCategory] = useState(null);

    useEffect(() => {
        fetch("/esim_devices.json")
            .then(response => response.json())
            .then(data => {
                if (data.devices) {
                    setDeviceData(data.devices);
                } else {
                    console.error("Invalid JSON structure: Missing 'devices' key", data);
                }
            })
            .catch(error => console.error("Error loading esim_devices.json: ", error));
    }, []);

    const toggleCategory = (category) => {
        setOpenCategory(openCategory === category ? null : category);
    };

    return (
        <div className="devices-container">
            <h2 className="devices-title">Supported eSIM Devices</h2>
            {deviceData.length === 0 ? (
                <p className="error-message">No devices found.</p>
            ) : (
                deviceData.map((brand) => (
                    <div key={brand.brand} className="brand-section">
                        <h3 className="brand-title">{brand.brand}</h3>
                        {brand.categories.map((category) => (
                            <div key={category.name} className="device-category">
                                <button className="category-button" onClick={() => toggleCategory(category.name)}>
                                    {category.name}
                                    <span className={`arrow ${openCategory === category.name ? "open" : ""}`}>▼</span>
                                </button>
                                {openCategory === category.name && (
                                    <ul className="device-list">
                                        {category.devices.map((device) => (
                                            <li key={device} className="device-item">{device}</li>
                                        ))}
                                    </ul>
                                )}
                            </div>
                        ))}
                    </div>
                ))
            )}
        </div>
    );
};

export default EsimDevices;
