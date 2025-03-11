// MyESIMs.js
import React, { useEffect, useState } from 'react';
import './myESIMs.css';

const MyESIMs = () => {
  const [esims, setEsims] = useState([]);
  // Read the TEST_MODE flag from environment variables.
  const testMode = process.env.REACT_APP_TEST_MODE === "true";

  useEffect(() => {
    if (testMode) {
      // Sample data for test mode
      const sampleEsims = [
        {
          id: 1,
          packageName: "Global 1GB",
          esimStatus: "Active",
          usage: "200 MB used",
          orderDate: "2025-03-01",
          expiredTime: "2025-04-01",
        },
        {
          id: 2,
          packageName: "Regional 5GB",
          esimStatus: "Active",
          usage: "1.2 GB used",
          orderDate: "2025-02-15",
          expiredTime: "2025-03-15",
        },
      ];
      setEsims(sampleEsims);
      console.log("[MyESIMs] TEST_MODE enabled: using sample data");
    } else {
      // In production, use an API call to fetch real data
      // Example (to be implemented later):
      // fetch('/api/myesims')
      //   .then(response => response.json())
      //   .then(data => setEsims(data.esims))
      console.log("[MyESIMs] Production mode: API call not implemented yet");
    }
  }, [testMode]);

  const handleTopUp = (id) => {
    // Placeholder: implement top-up logic (e.g., open a modal or call an API)
    alert(`Top-up data for eSIM ID ${id}`);
  };

  const handleCancel = (id) => {
    // Placeholder: implement cancellation and refund logic here
    if (window.confirm("Are you sure you want to cancel this eSIM and refund?")) {
      alert(`eSIM ID ${id} cancelled`);
    }
  };

  return (
    <div className="my-esims-container">
      <h2>My eSIMs</h2>
      {esims.length === 0 ? (
        <p>No active eSIMs found.</p>
      ) : (
        <table className="esims-table">
          <thead>
            <tr>
              <th>Package Name</th>
              <th>eSIM Status</th>
              <th>Usage</th>
              <th>Order Date</th>
              <th>Expired Time</th>
              <th>Options</th>
            </tr>
          </thead>
          <tbody>
            {esims.map((esim) => (
              <tr key={esim.id}>
                <td>{esim.packageName}</td>
                <td>{esim.esimStatus}</td>
                <td>{esim.usage}</td>
                <td>{esim.orderDate}</td>
                <td>{esim.expiredTime}</td>
                <td>
                  <button
                    className="topup-button"
                    onClick={() => handleTopUp(esim.id)}
                  >
                    📥 Top-up
                  </button>
                  <button
                    className="cancel-button"
                    onClick={() => handleCancel(esim.id)}
                  >
                    ❌ Cancel
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};

export default MyESIMs;
