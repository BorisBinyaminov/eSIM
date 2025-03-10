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

function MiniApp() {
  const [activePage, setActivePage] = useState("main");
  const [activeTab, setActiveTab] = useState("buy");
  const [menuOpen, setMenuOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);
  const [helpCenterOpen, setHelpCenterOpen] = useState(false);
  const [user, setUser] = useState(null); // holds authenticated user info

  const toggleHelpCenter = () => {
    setHelpCenterOpen((prev) => !prev);
  };

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth < 768);
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  // Attempt to auto-authenticate using Telegram WebApp data
  useEffect(() => {
    if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.initData) {
      const initData = window.Telegram.WebApp.initData;
      authService
        .authenticateTelegram(initData)
        .then((data) => {
          if (data.success) {
            setUser(data.user);
          } else {
            console.error("Auth failed:", data.error);
          }
        })
        .catch((err) => console.error("Auth error:", err));
    }
  }, []);

  // Logout: call the backend and clear user state
  const handleLogout = () => {
    authService.logoutTelegram().then(() => {
      setUser(null);
    });
  };

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

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (!event.target.closest(".menu-container") && menuOpen) {
        setMenuOpen(false);
      }
    };
    document.addEventListener("click", handleClickOutside);
    return () => document.removeEventListener("click", handleClickOutside);
  }, [menuOpen]);

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
              {user ? (
                <div className="user-info">
                  <img src={user.photo_url} alt="User Avatar" className="user-photo" />
                  <button className="nav-button" onClick={handleLogout}>
                    {user.username}
                  </button>
                </div>
              ) : (
                <button className="nav-button">Login</button>
              )}
              <a href="https://t.me/eSIM_Unlimited" target="_blank" rel="noopener noreferrer" className="nav-button">
                <img src="/images/general/telegram3.png" alt="Telegram" className="icon" /> Community
              </a>
              <a href="https://t.me/esim_unlimited_support_bot" target="_blank" rel="noopener noreferrer" className="nav-button">
                <img src="/images/general/telegram3.png" alt="Telegram" className="icon" /> Support
              </a>
            </div>
          )}
        </div>
      ) : (
        <div className="nav-buttons">
          {user ? (
            <div className="user-info">
              <img src={user.photo_url} alt="User Avatar" className="user-photo" />
              <button className="nav-button" onClick={handleLogout}>
                {user.username}
              </button>
            </div>
          ) : (
            <button className="nav-button">Login</button>
          )}
          <a href="https://t.me/eSIM_Unlimited" target="_blank" rel="noopener noreferrer" className="nav-button">
            <img src="/images/general/telegram3.png" alt="Telegram" className="icon" /> Community
          </a>
          <a href="https://t.me/esim_unlimited_support_bot" target="_blank" rel="noopener noreferrer" className="nav-button">
            <img src="/images/general/telegram3.png" alt="Telegram" className="icon" /> Support
          </a>
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

  const renderContent = () => (
    <div className="mini-app-container">
      {renderHeader()}
      {renderTabs()}
      {activePage === "main" ? (
        <div className="main-page">
          <header className="main-header">
            <h1 className="title">eSIM Unlimited</h1>
            <p className="subtitle">
              Stay connected in 150 countries with affordable eSIM packages
            </p>
          </header>
          <div className="cta-section">
            <button onClick={() => handleTabChange("buy")} className="cta-button">
              Get eSIM
            </button>
          </div>
        </div>
      ) : (
        <div className="tabs-page">
          <div className="tab-content">
            {activeTab === "buy" && <BuyESIM />}
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
