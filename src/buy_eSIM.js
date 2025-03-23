import React, { useState, useEffect, useRef, useMemo } from "react";
import "./buy_eSIM.css";

const BuyESIM = () => {
    // Initialize activeTab from localStorage or default to "local"
    const [activeTab, setActiveTab] = useState(() => localStorage.getItem("buyEsimActiveTab") || "local");
    const [countries, setCountries] = useState([]);
    // eslint-disable-next-line no-unused-vars
    const [regions, setRegions] = useState([]);
    const [countryPackages, setCountryPackages] = useState([]);
    const [selectedCountry, setSelectedCountry] = useState(null);
    const [selectedRegion, setSelectedRegion] = useState(null);
    const [searchQuery, setSearchQuery] = useState("");
    const searchRef = useRef(null);
    const [visibleCountries, setVisibleCountries] = useState(10);
    const [packages, setPackages] = useState([]);
    const [globalPackages, setGlobalPackages] = useState([]);
    const [filteredPackages, setFilteredPackages] = useState([]);
    const [selectedPackage, setSelectedPackage] = useState(null);
    const [expandedPackages, setExpandedPackages] = useState({});

    const packageTypes = {
        "Global 1GB": 1,
        "Global 3GB": 3,
        "Global 5GB": 5,
        "Global 10GB": 10,
        "Global 20GB": 20,
    };
    
    const regionIcons = useMemo(() => ({
        "Europe": ["/images/regions/europe.png", (pkg) => pkg.name.includes("Europe")],
        "South America": ["/images/regions/south_america.png", (pkg) => pkg.name.includes("South America")],
        "North America": ["/images/regions/north_america.png", (pkg) => pkg.name.includes("North America")],
        "Africa": ["/images/regions/africa.png", (pkg) => pkg.name.includes("Africa")],
        "Asia": ["/images/regions/asia.png", (pkg) => {
            return pkg.name.includes("Asia") || 
                   pkg.name.includes("Central Asia") || 
                   pkg.name.includes("Singapore") || 
                   pkg.name.includes("Gulf") || 
                   pkg.name.includes("China");
        }],
        "Caribbean": ["/images/regions/north_america.png", (pkg) => pkg.name.includes("Caribbean")]
    }), []);

    const formatVolume = (volume) => {
        let volumeGB = volume / (1024 * 1024 * 1024);
        volumeGB = Math.ceil(volumeGB * 10) / 10;
        return `${volumeGB}GB`;
    };

    // Persist activeTab to localStorage whenever it changes
    useEffect(() => {
        localStorage.setItem("buyEsimActiveTab", activeTab);
    }, [activeTab]);

    useEffect(() => {
        fetch("/countries.json")
            .then(response => response.json())
            .then(data => setCountries(Object.entries(data).map(([code, name]) => ({ code, name }))));
    }, []);

    useEffect(() => {
        if (regionIcons && Object.keys(regionIcons).length > 0) {
            setRegions(Object.keys(regionIcons));
            fetch("/regionalPackages.json")
                .then((response) => response.json())
                .then((data) => {
                    setPackages(data);
                })
                .catch((error) => console.error("Error loading regionalPackages.json:", error));
        } else {
            console.error("Error: regionIcons not loaded properly.");
        }
    }, [regionIcons]);

    const handleRegionClick = (region) => {
        setSelectedRegion(region);
        const matchingPackages = packages.filter(regionIcons[region]?.[1] || (() => false));
        setFilteredPackages(matchingPackages);
    };

    const filteredRegionPackages = useMemo(() => {
        if (!selectedRegion || !regionIcons[selectedRegion] || !regionIcons[selectedRegion][1]) {
            return [];
        }
        return packages
            .filter(regionIcons[selectedRegion][1])
            .sort((a, b) => a.retailPrice - b.retailPrice);
    }, [selectedRegion, packages, regionIcons]);

    const filteredGlobalPackages = selectedPackage
        ? globalPackages.filter(pkg => formatVolume(pkg.volume) === `${packageTypes[selectedPackage]}GB`)
            .sort((a, b) => a.retailPrice - b.retailPrice)
        : [];

    const handleCountryClick = (countryCode) => {
        setSelectedCountry(countryCode);
        setVisibleCountries(prev => prev); 
    };

    useEffect(() => {
        fetch("/countryPackages.json")
            .then(response => response.json())
            .then(data => {
                const uniqueCountryCodes = [...new Set(data.map(pkg => pkg.location))];
                setCountryPackages(data);
                return uniqueCountryCodes;
            })
            .then(uniqueCountryCodes => {
                fetch("/countries.json")
                    .then(response => response.json())
                    .then(data => {
                        let countryList = uniqueCountryCodes.map(code => ({
                            code,
                            name: data[code] || code,
                            flag: `/images/flags/${code.toLowerCase()}.png`
                        }));
                        countryList = countryList.sort((a, b) => a.name.localeCompare(b.name));
                        setCountries(countryList);
                    })
                    .catch(error => console.error("Error loading countries.json: ", error));
            })
            .catch(error => console.error("Error loading countryPackages.json: ", error));
    }, []);

    useEffect(() => {
        let isMounted = true;
        fetch("/globalPackages.json")
            .then((response) => response.json())
            .then((data) => {
                if (isMounted) setGlobalPackages(data);
            })
            .catch((error) => console.error("Error loading globalPackages.json: ", error));
        return () => { isMounted = false; };
    }, []);

    useEffect(() => {
        if (selectedCountry) {
            let packages = countryPackages
                .filter(pkg => pkg.location === selectedCountry) 
                .map(pkg => {
                    let volumeGB = pkg.volume / (1024 * 1024 * 1024);
                    volumeGB = volumeGB < 0.5 ? 0.5 : Math.ceil(volumeGB);
                    return { ...pkg, volumeGB: volumeGB + "GB" };
                })
                .sort((a, b) => a.retailPrice - b.retailPrice);
            setFilteredPackages(packages);
        }
    }, [selectedCountry, countryPackages]);

    const clearSearch = () => {
        setSearchQuery("");
    };

    const handlePackageClick = (packageType) => {
        setSelectedPackage(packageType);
    };

    const toggleExpand = (index) => {
        setExpandedPackages(prev => ({ ...prev, [index]: !prev[index] }));
    };

    useEffect(() => {
        if (!selectedCountry) {
            setVisibleCountries(prev => prev);
        }
    }, [selectedCountry]);

    const handleTabChange = (tab) => {
        setActiveTab(tab);
        setFilteredPackages([]);
        setSelectedCountry(null);
        setSelectedRegion(null);
        setSelectedPackage(null);
    };

    return (
        <div className="buy-esim-container">
            <h2>Buy eSIM</h2>
            <div className="esim-tabs">
                <button onClick={() => handleTabChange("local")} className={activeTab === "local" ? "active" : ""}>Local</button>
                <button onClick={() => handleTabChange("regional")} className={activeTab === "regional" ? "active" : ""}>Regional</button>
                <button onClick={() => handleTabChange("global")} className={activeTab === "global" ? "active" : ""}>Global</button>
            </div>
            
            {activeTab === "local" && (
              <>
                <h2>Select a Country</h2>
                <div className="search-container">
                  <div className="search-box" ref={searchRef}>
                    <input
                      type="text"
                      placeholder="Search country..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="search-input"
                    />
                    {searchQuery && (
                      <button className="clear-search" onClick={clearSearch}>&times;</button>
                    )}
                  </div>
                </div>

                <div className="country-list">
                  {countries
                    .filter(country => country.name.toLowerCase().includes(searchQuery.toLowerCase()))
                    .slice(0, visibleCountries)
                    .map(country => (
                    <button key={country.code} className="country-button" 
                        onClick={() => {
                            handleCountryClick(country.code);
                            setSelectedCountry(country.code);
                        }}>
                        <img src={country.flag} alt={country.name} className="flag-icon" />
                        <span className="country-name">{country.name}</span>
                    </button>
                    ))}
                </div>
                {visibleCountries < countries.length && (
                  <button className="show-more" onClick={() => setVisibleCountries(countries.length)}>Show More</button>
                )}
                {visibleCountries > 10 && (
                  <button className="show-less" onClick={() => setVisibleCountries(10)}>Show Less</button>
                )}
              </>
            )}
            {selectedCountry && (
                <div className="packages-container">
                    <h3>Available Packages for {countries.find(c => c.code === selectedCountry)?.name}</h3>
                    <div className="packages-list">
                        {filteredPackages.length > 0 ? (
                            <table className="packages-table">
                                <thead>
                                    <tr>
                                        <th>Data Volume</th>
                                        <th>Duration</th>
                                        <th>Price</th>
                                        <th>Top-Up Support</th>
                                        <th></th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {filteredPackages.map(pkg => (
                                        <tr key={pkg.packageCode}>
                                            <td>{pkg.volumeGB}</td>
                                            <td>{pkg.duration} {pkg.duration === 1 ? "day" : "days"}</td>
                                            <td>${(pkg.retailPrice / 10000).toFixed(2)}</td>
                                            <td>{pkg.supportTopUpType === 2 ? "Yes" : "No"}</td>
                                            <td><button className="buy-now">Buy Now!</button></td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        ) : (
                            <p>No packages available for this country.</p>
                        )}
                    </div>
                </div>
            )}
         
            {activeTab === "regional" && (
                <div>
                    <h3>Select a Region</h3>
                    <div className="region-buttons">
                        {Object.keys(regionIcons).map((region) => (
                            <button key={region} className="region-button" onClick={() => handleRegionClick(region)}>
                                <img src={regionIcons[region][0]} alt={region} className="region-icon" />
                                <span>{region}</span>
                            </button>
                        ))}
                    </div>
                    {selectedRegion && (
                        <div className="package-table">
                            <h3>Available Packages for {selectedRegion}</h3>
                            <table>
                                <thead>
                                    <tr>
                                        <th>Data Volume</th>
                                        <th>Duration</th>
                                        <th>Price</th>
                                        <th>Name</th>
                                        <th>Top-Up Support</th>
                                        <th>Coverage</th>
                                        <th>Locations</th>
                                        <th>Action</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {filteredRegionPackages.map((pkg, index) => {
                                        const locationNames = pkg.location.split(",").map(code => countries.find(c => c.code === code)?.name || code);
                                        const countryCodes = pkg.location.split(",");
                                        return (
                                            <tr key={index}>
                                                <td>{formatVolume(pkg.volume)}</td>
                                                <td>{pkg.duration} {pkg.duration === 1 ? "day" : "days"}</td>
                                                <td>${(pkg.retailPrice / 10000).toFixed(2)}</td>
                                                <td>{pkg.name}</td> 
                                                <td>{pkg.supportTopUpType === 2 ? "Yes" : "No"}</td>
                                                <td>{countryCodes.length} countries</td>
                                                <td>{locationNames.join(", ")}</td>
                                                <td><button className="buy-button">Buy Now</button></td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            )}
            
            {activeTab === "global" && (
                <div>
                    <h2>Select a Global eSIM Package</h2>
                    <div className="global-package-buttons">
                        {Object.keys(packageTypes).map((packageType) => (
                            <button 
                                key={packageType} 
                                className={`global-package-button ${selectedPackage === packageType ? 'selected' : ''}`} 
                                onClick={() => handlePackageClick(packageType)}
                            >
                                <img src="/images/global/globe.png" alt="Globe Icon" />
                                <span>{packageType}</span>
                            </button>
                        ))}
                    </div>
                    {selectedPackage && filteredGlobalPackages.length > 0 ? (
                        <div className="global-package-table">
                            <h3>Available Packages for {selectedPackage}</h3>
                            <table>
                                <thead>
                                    <tr>
                                        <th>Data Volume</th>
                                        <th>Duration</th>
                                        <th>Top-Up Support</th>
                                        <th>Coverage</th>
                                        <th>Supported Countries</th>
                                        <th>Price</th>
                                        <th>Action</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {filteredGlobalPackages.map((pkg, index) => {
                                        const countryCodes = pkg.location.split(",");
                                        const countryNames = countryCodes.map((code) => countries[code] || code);
                                        const isExpanded = expandedPackages[index];
                                        return (
                                            <tr key={index}>
                                                <td>{formatVolume(pkg.volume)}</td>
                                                <td>{pkg.duration} {pkg.duration === 1 ? "day" : "days"}</td>
                                                <td className={`top-up-support ${pkg.supportTopUpType === 2 ? 'yes' : 'no'}`}>
                                                    {pkg.supportTopUpType === 2 ? "Yes" : "No"}
                                                </td>
                                                <td>{countryCodes.length} countries</td>
                                                <td className="global-country-list" style={{ transition: 'max-height 0.3s ease-in-out', maxHeight: isExpanded ? '200px' : '40px', overflow: 'hidden' }}>
                                                    {isExpanded
                                                        ? countryNames.join(", ")
                                                        : countryNames.slice(0, 5).join(", ")}
                                                    {countryNames.length > 5 && (
                                                        <span 
                                                            className="global-show-more" 
                                                            onClick={() => toggleExpand(index)}
                                                            style={{ display: 'block', marginTop: '5px' }}
                                                        >
                                                            {isExpanded ? "[−] Show Less" : "[+] Show More"}
                                                        </span>
                                                    )}
                                                </td>
                                                <td className="price">${(pkg.retailPrice / 10000).toFixed(2)}</td>
                                                <td>
                                                    <button className="global-buy-button">Buy Now!</button>
                                                </td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                    ) : null}
                </div>
            )}
        </div>
    );
};

export default BuyESIM;
