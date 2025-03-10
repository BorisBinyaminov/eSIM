import React, { useState } from "react";
import "./Guides.css";

const Guides = () => {
  const [platform, setPlatform] = useState("ios");
  const [mode, setMode] = useState("installation");
  const [step, setStep] = useState(0);

  const data = {
    ios: {
      installation: [
        {
          step: 1,
          description: "On Settings > Tap Celular/Mobile Service.",
          image: process.env.PUBLIC_URL + "/images/IOS_installation/eSIM-EN-Orbister-iOS-installation-001.png",
        },
        {
          step: 2,
          description: "Tap Add Data Plan.",
          image: process.env.PUBLIC_URL + "/images/IOS_installation/eSIM-EN-Orbister-iOS-installation-002.png",
        },
		{
          step: 3,
          description: "Select Use QR Code.",
          image: process.env.PUBLIC_URL + "/images/IOS_installation/eSIM-EN-Orbister-iOS-installation-003.png",
        },
		{
          step: 4,
          description: "Scan the eSIM QR Code and complete the Add Data Plan installation. If not possible, share it with another device or print it.",
          image: process.env.PUBLIC_URL + "/images/IOS_installation/eSIM-EN-Orbister-iOS-installation-004.png",
        },
		{
          step: 5,
          description: "Tap Continue.",
          image: process.env.PUBLIC_URL + "/images/IOS_installation/eSIM-EN-Orbister-iOS-installation-005.png",
        },
		{
          step: 6,
          description: "Tap Done.",
          image: process.env.PUBLIC_URL + "/images/IOS_installation/eSIM-EN-Orbister-iOS-installation-006.png",
        },
		{
          step: 7,
          description: "Tap to rename your eSIM plan.",
          image: process.env.PUBLIC_URL + "/images/IOS_installation/eSIM-EN-Orbister-iOS-installation-007.png",
        },
		{
          step: 8,
          description: "Rename your eSIM plan.",
          image: process.env.PUBLIC_URL + "/images/IOS_installation/eSIM-EN-Orbister-iOS-installation-008.png",
        },
		{
          step: 9,
          description: "Tap Continue.",
          image: process.env.PUBLIC_URL + "/images/IOS_installation/eSIM-EN-Orbister-iOS-installation-009.png",
        },
		{
          step: 10,
          description: "Setup “Primary” as Default Line.",
          image: process.env.PUBLIC_URL + "/images/IOS_installation/eSIM-EN-Orbister-iOS-installation-010.png",
        },
		{
          step: 11,
          description: "Setup “Primary” as Mobile Data.",
          image: process.env.PUBLIC_URL + "/images/IOS_installation/eSIM-EN-Orbister-iOS-installation-011.png",
        },
		{
          step: 12,
          description: "Setup “Primary” as iMessage & FaceTime.",
          image: process.env.PUBLIC_URL + "/images/IOS_installation/eSIM-EN-Orbister-iOS-installation-012.png",
        },
      ],
      activation: [
        {
          step: 1,
          description: "On Settings > Tap Celular/Mobile Service.",
          image: process.env.PUBLIC_URL + "/images/IOS_activation/eSIM-EN-Orbister-iOS-activation-001.png",
        },
        {
          step: 2,
          description: "Tap on your eSIM.",
          image: process.env.PUBLIC_URL + "/images/IOS_activation/eSIM-EN-Orbister-iOS-activation-002.png",
        },
		{
          step: 3,
          description: "Tap to activate.",
          image: process.env.PUBLIC_URL + "/images/IOS_activation/eSIM-EN-Orbister-iOS-activation-003.png",
        },
		{
          step: 4,
          description: "After activating go back.",
          image: process.env.PUBLIC_URL + "/images/IOS_activation/eSIM-EN-Orbister-iOS-activation-004.png",
        },
		{
          step: 5,
          description: "Tap Mobile Data.",
          image: process.env.PUBLIC_URL + "/images/IOS_activation/eSIM-EN-Orbister-iOS-activation-005.png",
        },
		{
          step: 6,
          description: "After selected go back.",
          image: process.env.PUBLIC_URL + "/images/IOS_activation/eSIM-EN-Orbister-iOS-activation-006.png",
        },
		{
          step: 7,
          description: "Tap your eSIM.",
          image: process.env.PUBLIC_URL + "/images/IOS_activation/eSIM-EN-Orbister-iOS-activation-007.png",
        },
		{
          step: 8,
          description: "Tap to activate Data Roaming.",
          image: process.env.PUBLIC_URL + "/images/IOS_activation/eSIM-EN-Orbister-iOS-activation-008.png",
        },
		{
          step: 9,
          description: "All set. Enjoy you can now start using your eSIM’s data plan.",
          image: process.env.PUBLIC_URL + "/images/IOS_activation/eSIM-EN-Orbister-iOS-activation-009.png",
        },
      ],
    },
    android: {
      installation: [
        {
          step: 1,
          description: "On Settings > Tap Connections.",
          image: process.env.PUBLIC_URL + "/images/Android_installation/eSIM-EN-Orbister-Android-installation-001.png",
        },
        {
          step: 2,
          description: "Tap SIM Manager.",
          image: process.env.PUBLIC_URL + "/images/Android_installation/eSIM-EN-Orbister-Android-installation-002.png",
        },
		{
          step: 3,
          description: "Tap Add eSIM.",
          image: process.env.PUBLIC_URL + "/images/Android_installation/eSIM-EN-Orbister-Android-installation-003.png",
        },
		{
          step: 4,
          description: "Tap Scan QR code. If not possible, share it with another device or print it.",
          image: process.env.PUBLIC_URL + "/images/Android_installation/eSIM-EN-Orbister-Android-installation-004.png",
        },
		{
          step: 5,
          description: "Get the QR code sent to you.",
          image: process.env.PUBLIC_URL + "/images/Android_installation/eSIM-EN-Orbister-Android-installation-005.png",
        },
		{
          step: 6,
          description: "Scan QR code.",
          image: process.env.PUBLIC_URL + "/images/Android_installation/eSIM-EN-Orbister-Android-installation-006.png",
        },
		{
          step: 7,
          description: "Tap Add.",
          image: process.env.PUBLIC_URL + "/images/Android_installation/eSIM-EN-Orbister-Android-installation-007.png",
        },
		{
          step: 8,
          description: "Tap the new added eSIM.",
          image: process.env.PUBLIC_URL + "/images/Android_installation/eSIM-EN-Orbister-Android-installation-008.png",
        },
		{
          step: 9,
          description: "Tap Name to rename you eSIM.",
          image: process.env.PUBLIC_URL + "/images/Android_installation/eSIM-EN-Orbister-Android-installation-009.png",
        },
		{
          step: 10,
          description: "Rename your eSIM, and after tap done.",
          image: process.env.PUBLIC_URL + "/images/Android_installation/eSIM-EN-Orbister-Android-installation-010.png",
        },
		{
          step: 11,
          description: "You're all set. You can now confirm the eSIM has been installed and renamed.",
          image: process.env.PUBLIC_URL + "/images/Android_installation/eSIM-EN-Orbister-Android-installation-011.png",
        },
      ],
      activation: [
        {
          step: 1,
          description: "On Settings > Tap Connections.",
          image: process.env.PUBLIC_URL + "/images/Android_activation/eSIM-EN-Orbister-Android-activation-001.png",
        },
        {
          step: 2,
          description: "Tap SIM Manager.",
          image: process.env.PUBLIC_URL + "/images/Android_activation/eSIM-EN-Orbister-Android-activation-002.png",
        },
		{
		  step: 3,
          description: "Turn 'ON' the eSIM.",
          image: process.env.PUBLIC_URL + "/images/Android_activation/eSIM-EN-Orbister-Android-activation-003.png",
        },
		{
		  step: 4,
          description: "Tap Mobile Data.",
          image: process.env.PUBLIC_URL + "/images/Android_activation/eSIM-EN-Orbister-Android-activation-004.png",
        },
		{
		  step: 5,
          description: "Select your eSIM from the list.",
          image: process.env.PUBLIC_URL + "/images/Android_activation/eSIM-EN-Orbister-Android-activation-005.png",
        },
		{
		  step: 6,
          description: "Make sure that Mobile Data is set to your eSIM.",
          image: process.env.PUBLIC_URL + "/images/Android_activation/eSIM-EN-Orbister-Android-activation-006.png",
        },
		{
		  step: 7,
          description: "Go to the previous screen and tap Mobile networks.",
          image: process.env.PUBLIC_URL + "/images/Android_activation/eSIM-EN-Orbister-Android-activation-007.png",
        },
		{
		  step: 8,
          description: "Turn 'ON' Data roaming.",
          image: process.env.PUBLIC_URL + "/images/Android_activation/eSIM-EN-Orbister-Android-activation-008.png",
        },
		{
		  step: 9,
          description: "Make sure that 'Data roaming' is 'ON' and you can start using your eSIM’s data plan.",
          image: process.env.PUBLIC_URL + "/images/Android_activation/eSIM-EN-Orbister-Android-activation-009.png",
        },
      ],
    },
  };

  const steps = data[platform][mode];

  const handlePlatformChange = (selectedPlatform) => {
    setPlatform(selectedPlatform);
    setStep(0);
  };

  const handleModeChange = (selectedMode) => {
    setMode(selectedMode);
    setStep(0);
  };

  const handleNext = () => {
    if (step < steps.length - 1) {
      setStep(step + 1);
    }
  };

  const handlePrevious = () => {
    if (step > 0) {
      setStep(step - 1);
    }
  };

  return (
    <div className="guide-container">
      <div className="platform-tabs">
        <button
          onClick={() => handlePlatformChange("ios")}
          className={platform === "ios" ? "active" : ""}
        >
          iOS
        </button>
        <button
          onClick={() => handlePlatformChange("android")}
          className={platform === "android" ? "active" : ""}
        >
          Android
        </button>
      </div>
      <div className="platform-tabs">
        <button
          onClick={() => handleModeChange("installation")}
          className={mode === "installation" ? "active" : ""}
        >
          Installation
        </button>
        <button
          onClick={() => handleModeChange("activation")}
          className={mode === "activation" ? "active" : ""}
        >
          Activation
        </button>
      </div>
      <h2 className="guide-title">
        {platform.toUpperCase()} {mode.charAt(0).toUpperCase() + mode.slice(1)}
      </h2>
      <p>Step {step + 1} of {steps.length}</p>
      <div className="guide-image-wrapper">
        <button
          className="arrow"
          onClick={handlePrevious}
          disabled={step === 0}
        >
          &#9664;
        </button>
        <img
          src={steps[step].image}
          alt={`Step ${step + 1}`}
          className="guide-image"
        />
        <button
          className="arrow"
          onClick={handleNext}
          disabled={step === steps.length - 1}
        >
          &#9654;
        </button>
      </div>
      <p>{steps[step].description}</p>
      <div className="navigation-buttons">
        <button onClick={handlePrevious} disabled={step === 0}>
          Previous
        </button>
        <button onClick={handleNext} disabled={step === steps.length - 1}>
          Next
        </button>
      </div>
    </div>
  );
};

export default Guides;
