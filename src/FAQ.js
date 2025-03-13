import React, { useState } from "react";

const FAQ = () => {
  const [activeIndex, setActiveIndex] = useState(null);

const faqs = [
    {
      question: "Which devices and software versions support eSIM?",
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
      question: "How to set up eSIM for iOS/Android?",
      answer: `
        - Purchase an eSIM data plan on our website.
        - Receive the eSIM QR code by email.
        - Follow instructions in our Help Center->Guides`,
    },
    {
      question: "How fast is the network speed?",
      answer: "4G/LTE service is available in most countries, in some countries 5G is also available.",
    },
    {
      question: "Are voice calls and SMS included?",
      answer: "Only data service is available.",
    },
    {
      question: "Can I use more than one eSIM provider when traveling abroad?",
      answer: "Yes, iPhones can store 10 eSIMs, and Androids can store 5-7 eSIMs. Only one eSIM can be active at a time. Label eSIMs to avoid confusion.",
    },
    {
      question: "How to use hotspots with eSIM?",
      answer: "On iOS, APNs are preconfigured except for Japan (set APN to be “vmobile.jp”). For Android issues, contact customer service for support.",
    },
    {
      question: "How to use dual SIM on iPhone and set up eSIM?",
      answer: `
        Dual SIM offers separate voice/SMS and data plans. Follow specific iPhone steps to configure eSIM for cellular data only.`,
    },
    {
      question: "Should I switch on Data Roaming when using eSIM?",
      answer: `Yes. Ensure that "Data Roaming" is turned ON during use.`,
    },
    {
      question: "How to remove the eSIM data plan after use?",
      answer: "Use your phone's delete eSIM function in settings.",
    },
    {
      question: "How do I get my eSIM after payment?",
      answer: `You will receive an email with your QR code. Check your spam folder if it doesn't arrive within a minute.`,
    },
    {
      question: "How is the validity period of the plan calculated?",
      answer: `Validity starts from your eSIM's first connection, as described in the package information.`,
    },
    {
      question: "When does the billing period or validity start?",
      answer: `Data plans will only begin counting usage once customers make their first connection to the local network.`,
    },
    {
      question: "How to check the balance of remaining data?",
      answer: `Check "My eSIMs" tab in our mini app or telegram bot.`,
    },
    {
      question: "How to Top Up a data plan?",
      answer: `Top Up is available in My eSIMs tab.`,
    },
    {
      question: "How do I refund an unused order?",
      answer: `in My eSIMs tab, You can use the Cancel feature to refund an unused (not installed) eSIM order.`,
    },
    {
      question: "What does each eSIM status mean?",
      answer: `Here are the eSIM status and their definitions:
        - Provisioning - Newly purchased eSIM being created by the server.
        - New - Newly created eSIM, ready for installation.
        - Onboard - Newly installed eSIM, waiting for first use, no data use.
        - In Use - Installed eSIM serving data from a data plan.
        - Depleted - Installed eSIM having consumed available data.
        - Canceled - Newly purchased eSIM, refunded and returned to inventory.
        - Deleted - eSIM uninstalled from user device or eSIM, revoked or eSIM Invalid.
        - Suspended - Installed eSIM currently disabled.`,
    },
    {
      question: "Can I use one eSIM for two devices?",
      answer: `No, an eSIM can only be used on one device at a time. If you want to use eSIM services on another device, you will need to transfer the eSIM.`,
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
      answer: "eSIM is compatible with a wide range of devices that support eSIM technology. For a detailed list of supported devices, please visit our Help Center->Supported Devices.",
    },
    {
      question: "Can I reuse an eSIM?",
      answer: "Your eSIM won't be available to transfer if you have already activated. You could still enjoy eSIM if you haven't activated it before changing the device.",
    },
    {
      question: "How do I transfer an eSIM to another device?",
      answer: `You can transfer your not activated eSIM to another device.
	To transfer:
		- Remove the eSIM from the current device (uninstall or delete from settings).
		- Use the same QR code or activation method on the new device.
		- Follow the on-screen instructions to complete the setup on the new device.`,
    },
    {
      question: "What if I erased my eSIM plan by accident?",
      answer: `DO NOT delete your eSIM when you haven't used up your data.
      - Try to reinstall from the original QR code.
      - If you accidentally delete your eSIM after your activation, you may have to purchase a new eSIM.`,
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
