import React, { useState } from "react";

const FAQ = () => {
  const [activeIndex, setActiveIndex] = useState(null);

const faqs = [
    {
      question: "How can I use the eSIM service?",
      answer: `
        - **iOS:** You must have iOS 12.1 or later and an unlocked iPhone. iPhones older than XR or XS support eSIM. 
          (Note: If you purchased your phone under a contract, check with your carrier to unlock eSIM compatibility.)
        - **Android:** Samsung, Pixel, and many Android devices support eSIM.`,
    },
    {
      question: "In what scenarios can eSIM service be used?",
      answer: `
        - Add a local data plan when traveling internationally.
        - Use eSIM for data while keeping your primary SIM for voice and SMS.`,
    },
    {
      question: "How to set up eSIM for iOS?",
      answer: `
        - Purchase an eSIM data plan on our website.
        - Receive the eSIM QR code by email.
        - Set up eSIM:
          1. Go to [Settings] > [Cellular or Mobile Data] > [Add Cellular Plan].
          2. Scan the QR code provided by email.
          3. Follow additional instructions to label the plan and set it for cellular data only.`,
    },
    {
      question: "How to set up eSIM for Android?",
      answer: `
        - Purchase an eSIM data plan on our website.
        - Receive the eSIM QR code by email.
        - Set up eSIM:
          1. Go to [Settings] > [Network & Internet] > [Mobile Network].
          2. Tap "Download a SIM instead?" and follow the prompts.
          3. Scan the QR code and complete the setup.`,
    },
    {
      question: "How fast is the network speed?",
      answer: "4G/LTE service is available in most countries.",
    },
    {
      question: "Are voice calls and SMS included?",
      answer: "Only data service is available.",
    },
    {
      question: "How to use dual SIM on iPhone and set up eSIM?",
      answer: `
        Dual SIM offers separate voice/SMS and data plans. Follow specific iPhone steps to configure eSIM for cellular data only.`,
    },
    {
      question: "Should I switch on Data Roaming when using eSIM?",
      answer: `Yes. Ensure that "Data Roaming" is turned on during use.`,
    },
    {
      question: "How to remove the eSIM data plan after use?",
      answer: "Use your phone's delete eSIM function in settings.",
    },
    {
      question: "How do I get my eSIM after payment?",
      answer: `You will receive an email with your QR code. Check your spam folder if it doesn’t arrive within a minute.`,
    },
    {
      question: "How is the validity period of the plan calculated?",
      answer: `Validity starts from your eSIM's first connection, as described in the package information.`,
    },
    {
      question: "How to check the balance of remaining data?",
      answer: `Check [Settings - Cellular] on your phone to monitor data usage.`,
    },
    {
      question: "Can I use one eSIM for two devices?",
      answer: `No, an eSIM can only be used on one device at a time. If you want to use eSIM services on another device, you will need to transfer the eSIM, which can be done up to three times.`,
    },
    {
      question: "If I lost my eSIM QR code, what can I do?",
      answer: "Check your email or contact support.",
    },
    {
      question: "Will my physical SIM still work while eSIM is installed?",
      answer: `Yes, your physical SIM will still work. Turn off data roaming for it and enable "WiFi calling."`,
    },
    {
      question: "What devices are supported?",
      answer: "eSIM is compatible with a wide range of devices that support eSIM technology. For a detailed list of supported devices, please visit our Book Page for the information on compatibility.",
    },
    {
      question: "Can I reuse an eSIM?",
      answer: "Yes, you can reuse your eSIM by transferring it to another device. However, please note that each eSIM can only be transferred a maximum of three times.",
    },
    {
      question: "How do I transfer an eSIM to another device?",
      answer: `You can transfer your eSIM to another device up to three times.
	To transfer:
		- Remove the eSIM from the current device (uninstall or delete from settings).
		- Use the same QR code or activation method on the new device.
		- Follow the on-screen instructions to complete the setup on the new device.`,
    },
];


  const toggleFAQ = (index) => {
    setActiveIndex(activeIndex === index ? null : index);
  };

  return (
    <div className="faq-container">
      {faqs.map((faq, index) => (
        <div key={index} className={`faq-item ${activeIndex === index ? "active" : ""}`}>
          <div className="faq-question" onClick={() => toggleFAQ(index)}>
            <span className="faq-number">{String(index + 1).padStart(2, "0")}</span>
            {faq.question}
            <span className="faq-toggle">{activeIndex === index ? "▲" : "▼"}</span>
          </div>
          {activeIndex === index && (
            <div className="faq-answer">
              <p dangerouslySetInnerHTML={{ __html: faq.answer }}></p>
            </div>
          )}
        </div>
      ))}
    </div>
  );
};

export default FAQ;
