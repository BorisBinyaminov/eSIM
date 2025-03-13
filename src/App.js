import React, { useState, useEffect } from "react";
import "./App.css";
import FAQTab from "./FAQ";
import "./FAQ.css";
import Guides from "./Guides";
import "./Guides.css";
import EsimSupportedDevices from "./esim_devices";
import BuyESIM from "./buy_eSIM";
import "./buy_eSIM.css";
import "./localPackages.css";
import "./regionalPackages.css";
import "./globalPackages.css";
import authService from "./auth";  // dedicated FE auth service
import MyESIMs from "./myEsims";   // component for "My eSIMs" tab

function MiniApp() {
  // Initialize activePage and activeTab from localStorage or default values.
  const [activePage, setActivePage] = useState(() => localStorage.getItem("activePage") || "main");
  const [activeTab, setActiveTab] = useState(() => localStorage.getItem("activeTab") || "buy");
  const [menuOpen, setMenuOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);
  const [helpCenterOpen, setHelpCenterOpen] = useState(false);
  const [user, setUser] = useState(null); // holds authenticated user info

  const toggleHelpCenter = () => {
    setHelpCenterOpen((prev) => !prev);
  };

  // Update localStorage when activePage changes
  useEffect(() => {
    localStorage.setItem("activePage", activePage);
  }, [activePage]);

  // Update localStorage when activeTab changes
  useEffect(() => {
    localStorage.setItem("activeTab", activeTab);
  }, [activeTab]);

  // Update isMobile on window resize
  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth < 768);
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  // For development testing only: inject a fake Telegram object if not present.
  if (!window.Telegram) {
    const sampleInitData = "user=%7B%22id%22%3A12345%2C%22username%22%3A%22testuser%22%2C%22photo_url%22%3A%22%2Fimages%2Flogo%2Flogo.png%22%7D&hash=fakehash";
    window.Telegram = {
      WebApp: {
        initData: sampleInitData,
        initDataUnsafe: {
          id: 12345,
          username: "testuser",
          photo_url: "/images/logo/logo.png",
        },
        close: () => console.log("Simulated close"),
      },
    };
    console.log("Fake Telegram.WebApp object injected for testing.");
  }

  // Debug: Check if Telegram WebApp object is available
  useEffect(() => {
    if (window.Telegram && window.Telegram.WebApp) {
      console.log("Telegram WebApp object found.");
      console.log("initData:", window.Telegram.WebApp.initData);
    } else {
      console.log("Telegram WebApp not detected.");
    }
  }, []);

  // Auto-authenticate if Telegram initData is available
  useEffect(() => {
    if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.initData) {
      const initData = window.Telegram.WebApp.initData;
      authService
        .authenticateTelegram(initData)
        .then((data) => {
          if (data.success) {
            setUser(data.user);
            console.log("Auto-auth success:", data.user);
          } else {
            console.error("Auto-auth failed:", data.error);
          }
        })
        .catch((err) => console.error("Auto-auth error:", err));
    }
  }, []);

  // Manual login handler in case auto-auth does not occur.
  const handleManualLogin = () => {
    console.log("Manual login triggered.");
    if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.initData) {
      const initData = window.Telegram.WebApp.initData;
      authService
        .authenticateTelegram(initData)
        .then((data) => {
          if (data.success) {
            setUser(data.user);
            console.log("Manual auth success:", data.user);
          } else {
            console.error("Manual auth failed:", data.error);
          }
        })
        .catch((err) => console.error("Manual auth error:", err));
    } else {
      console.log("Telegram WebApp not detected on manual login.");
    }
  };

  // Logout handler: call backend and clear user state
  const handleLogout = () => {
    authService.logoutTelegram().then(() => {
      setUser(null);
      console.log("User logged out.");
    });
  };

  // Change tab logic: "main" resets, others set activeTab and change activePage to "tabs"
  const handleTabChange = (tab) => {
    if (tab === "main") {
      setActivePage("main");
      setActiveTab("");
    } else {
      setActiveTab(tab);
      setActivePage("tabs");
    }
  };

  const toggleMenu = (event) => {
    event.stopPropagation();
    setMenuOpen((prev) => !prev);
  };

  // Close menu if clicked outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (!event.target.closest(".menu-container") && menuOpen) {
        setMenuOpen(false);
      }
    };
    document.addEventListener("click", handleClickOutside);
    return () => document.removeEventListener("click", handleClickOutside);
  }, [menuOpen]);

  // Close help dropdown if clicked outside
  useEffect(() => {
    const handleClickOutsideHelp = (event) => {
      if (!event.target.closest(".help-center-container") && helpCenterOpen) {
        setHelpCenterOpen(false);
      }
    };
    document.addEventListener("click", handleClickOutsideHelp);
    return () => document.removeEventListener("click", handleClickOutsideHelp);
  }, [helpCenterOpen]);

  const renderHeader = () => (
    <header className="app-header">
      <div className="logo">eSIM Unlimited</div>
      {isMobile ? (
        <div className="menu-container">
          <button className="menu-icon" onClick={toggleMenu}>
            ☰
          </button>
          {menuOpen && (
            <div className="dropdown-menu">
              <a
                href="https://t.me/esim_unlimited_support_bot"
                target="_blank"
                rel="noopener noreferrer"
                className="nav-button"
              >
                <img src="/images/general/telegram3.png" alt="Telegram" className="icon" /> Support
              </a>
              <a
                href="https://t.me/eSIM_Unlimited"
                target="_blank"
                rel="noopener noreferrer"
                className="nav-button"
              >
                <img src="/images/general/telegram3.png" alt="Telegram" className="icon" /> Community
              </a>
              {user ? (
                <div className="user-info">
                  <img src={user.photo_url} alt="User Avatar" className="user-photo" />
                  <span className="nav-button">{user.username}</span>
                  <button className="nav-button" onClick={handleLogout}>
                    Logout
                  </button>
                </div>
              ) : (
                <button className="nav-button" onClick={handleManualLogin}>
                  Login
                </button>
              )}
            </div>
          )}
        </div>
      ) : (
        <div className="nav-buttons">
          <a
            href="https://t.me/esim_unlimited_support_bot"
            target="_blank"
            rel="noopener noreferrer"
            className="nav-button"
          >
            <img src="/images/general/telegram3.png" alt="Telegram" className="icon" /> Support
          </a>
          <a
            href="https://t.me/eSIM_Unlimited"
            target="_blank"
            rel="noopener noreferrer"
            className="nav-button"
          >
            <img src="/images/general/telegram3.png" alt="Telegram" className="icon" /> Community
          </a>
          {user ? (
            <div className="user-info">
              <img src={user.photo_url} alt="User Avatar" className="user-photo" />
              <span className="nav-button">{user.username}</span>
              <button className="nav-button" onClick={handleLogout}>
                Logout
              </button>
            </div>
          ) : (
            <button className="nav-button" onClick={handleManualLogin}>
              Login
            </button>
          )}
        </div>
      )}
    </header>
  );

  const renderTabs = () => (
    <div className="tab-header">
      <div className="nav-links">
        <button className="tab-button" onClick={() => setActivePage("main")}>
          Home
        </button>
        <button className="tab-button" onClick={() => handleTabChange("buy")}>
          Buy eSIM
        </button>
        <button className="tab-button" onClick={() => handleTabChange("myesims")}>
          My eSIMs
        </button>
        <div className="help-center-container">
          <button className="tab-button help-center-button" onClick={toggleHelpCenter}>
            Help Center ▼
          </button>
          {helpCenterOpen && (
            <div className="help-center-dropdown">
              <button onClick={() => handleTabChange("guides")}>Guides</button>
              <button onClick={() => handleTabChange("faq")}>FAQ</button>
              <button onClick={() => handleTabChange("devices")}>Supported Devices</button>
            </div>
          )}
        </div>
      </div>
    </div>
  );

  // Interactive Setup Guide Component defined directly here
  const InteractiveSetupGuide = ({ onCTAClick }) => {
    const [currentStep, setCurrentStep] = useState(0);
    const steps = [
      {
        number: 1,
        title: "Choose eSIM Data Plan",
        description:
          "Pick an eSIM data plan that suits your needs. Stay connected with the entire world, anytime, anywhere.",
      },
      {
        number: 2,
        title: "Easy Installation of eSIM",
        description:
          "Follow our simple step-by-step guide and scan the QR code for digital installation.",
      },
      {
        number: 3,
        title: "Easy Activation of eSIM",
        description:
          "Follow our simple step-by-step guide for digital activation.",
      },
      {
        number: 4,
        title: "Done! You Are Online",
        description:
          "Enjoy fast and reliable internet, calls, and text messages with your newly activated eSIM.",
      },
    ];

    const handleNext = () => {
      if (currentStep < steps.length - 1) {
        setCurrentStep(currentStep + 1);
      }
    };

    const handlePrev = () => {
      if (currentStep > 0) {
        setCurrentStep(currentStep - 1);
      }
    };

    return (
      <div className="setup-guide-section">
        <h2 className="section-headline">eSIM Setup Guide</h2>
        <p className="subtitle">Take these 3 easy steps to get eSIM on your phone!</p>
        {/* Progress Indicator */}
        <div className="progress-indicator">
          {steps.map((step, index) => (
            <div
              key={index}
              className={`progress-step ${index === currentStep ? "active" : ""}`}
            >
              {step.number}
            </div>
          ))}
        </div>
        {/* Step Content */}
        <div className="step-content">
        <div className="step-item">
          <h3>{steps[currentStep].title}</h3>
          <p>{steps[currentStep].description}</p>
        </div>
      </div>
        {/* Navigation Buttons */}
        <div className="step-navigation">
          {currentStep > 0 && (
            <button onClick={handlePrev} className="nav-button">
              Previous
            </button>
          )}
          {currentStep < steps.length - 1 ? (
            <button onClick={handleNext} className="nav-button">
              Next
            </button>
          ) : (
            <button onClick={onCTAClick} className="cta-button secondary-cta">
              Get Mobile Data
            </button>
          )}
        </div>
      </div>
    );
  };

  const renderMainPage = () => {
    return (
      <div className="main-page">
        {/* 1) Existing Headline, Subtext, and Primary CTA */}
        <header className="main-header">
          <h1 className="title">Stay Connected Anywhere with eSIM Unlimited</h1>
          <p className="subtitle">
            High-speed internet in 150+ countries. No roaming fees, no hidden charges, and no physical SIM required.
          </p>
        </header>
        <div className="cta-section">
          {/* Primary CTA Button */}
          <button onClick={() => handleTabChange("buy")} className="cta-button primary-cta">
            Buy eSIM
          </button>
        </div>
  
        {/* 2) Our Advantages Section */}
      <div className="our-advantages-section">
        <h2 className="section-headline">Our Advanced Features</h2>
        <div className="advantages-grid">
          <div className="advantage-item">
            <img src="/images/advantages/transfer.svg" alt="Two-way" className="advantage-icon" />
            <h3>Two-way Calls and Messages</h3>
            <p>Send or receive messages and Calls on any device, anytime, anywhere.</p>
          </div>
          <div className="advantage-item">
            <img src="/images/advantages/wallet.svg" alt="Payment" className="advantage-icon" />
            <h3>Convenient Payment Options</h3>
            <p>Securely complete transactions with our advanced payment system, supporting both credit cards and cryptocurrency.</p>
          </div>
          <div className="advantage-item">
            <img src="/images/advantages/support.svg" alt="Support" className="advantage-icon" />
            <h3>24/7 Customer Support</h3>
            <p>Have any questions? Contact us at the click of a button, and we will address them promptly.</p>
          </div>
          <div className="advantage-item">
            <img src="/images/advantages/glasses.svg" alt="Transparent" className="advantage-icon" />
            <h3>Transparent Conditions</h3>
            <p>No hidden fees, no roaming fees—just transparent conditions.</p>
          </div>
          <div className="advantage-item">
            <img src="/images/advantages/device.svg" alt="Transparent" className="advantage-icon" />
            <h3>User-friendly Interface</h3>
            <p>With intuitive design and comprehensive multilingual support, you're one tap away from convenience.</p>
          </div>
          <div className="advantage-item">
            <img src="/images/advantages/device-vibro.svg" alt="Transparent" className="advantage-icon" />
            <h3>Swift and Smooth Setup</h3>
            <p>Get your eSIM up and running in no time! Simply find your ideal plan from the diverse selection, and activate!</p>
          </div>
        </div>
        <div className="advantages-cta">
        <button 
            className="cta-button secondary-cta"
            onClick={() => handleTabChange("buy")}
          >
            Try Now
          </button>
        </div>
      </div>

        {/* 3) Setup Guide Section using the Interactive Component */}
        <InteractiveSetupGuide onCTAClick={() => handleTabChange("buy")} />
      </div>
    );
  };
  
  const renderContent = () => (
    <div className="mini-app-container">
      {renderHeader()}
      {renderTabs()}
      {activePage === "main" ? (
        renderMainPage()
      ) : (
        <div className="tabs-page">
          <div className="tab-content">
            {activeTab === "buy" && <BuyESIM />}
            {activeTab === "myesims" && <MyESIMs />}
            {activeTab === "guides" && <Guides />}
            {activeTab === "faq" && <FAQTab />}
            {activeTab === "devices" && <EsimSupportedDevices />}
          </div>
        </div>
      )}
    </div>
  );
  
  return renderContent();
}

export default MiniApp;
