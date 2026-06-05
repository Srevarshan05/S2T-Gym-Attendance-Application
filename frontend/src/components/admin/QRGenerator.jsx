import React, { useState, useEffect, useRef } from "react";
import QRCode from "qrcode";

const CHECKIN_URL_PROD = `${window.location.origin}/checkin`;
const CHECKIN_URL_DEV = `${window.location.protocol}//${window.location.hostname}:5173/checkin`;

export default function QRGenerator() {
  const canvasRef = useRef(null);
  const [url, setUrl] = useState(CHECKIN_URL_DEV);
  const [generated, setGenerated] = useState(false);

  const generateQR = async () => {
    if (!canvasRef.current) return;
    await QRCode.toCanvas(canvasRef.current, url, {
      width: 280,
      margin: 2,
      color: { dark: "#111827", light: "#ffffff" },
      errorCorrectionLevel: "H",
    });
    setGenerated(true);
  };

  useEffect(() => { generateQR(); }, [url]);

  const downloadQR = () => {
    if (!canvasRef.current) return;
    const link = document.createElement("a");
    link.download = "s2t-gym-checkin-qr.png";
    link.href = canvasRef.current.toDataURL("image/png");
    link.click();
  };

  return (
    <div className="bg-[#111827] rounded-2xl p-5 space-y-4">
      <div>
        <p className="text-[10px] uppercase tracking-widest font-bold text-[#4ADE80]">Gym Entrance QR</p>
        <h3 className="text-base font-black text-white mt-0.5">Attendance Check-In QR Code</h3>
        <p className="text-[10px] text-gray-400 mt-1">Print and display at the gym entrance. Members scan to log attendance.</p>
      </div>

      {/* URL selector */}
      <div className="space-y-2">
        <p className="text-[10px] text-gray-400 uppercase tracking-wider font-bold">QR Target URL</p>
        <div className="grid grid-cols-2 gap-2">
          <button onClick={() => setUrl(CHECKIN_URL_DEV)}
            className={`py-2 rounded-full text-[10px] font-bold transition-all cursor-pointer ${url === CHECKIN_URL_DEV ? "bg-[#4ADE80] text-[#111827]" : "bg-white/10 text-gray-400 hover:bg-white/20"}`}>
            Development
          </button>
          <button onClick={() => setUrl(CHECKIN_URL_PROD)}
            className={`py-2 rounded-full text-[10px] font-bold transition-all cursor-pointer ${url === CHECKIN_URL_PROD ? "bg-[#4ADE80] text-[#111827]" : "bg-white/10 text-gray-400 hover:bg-white/20"}`}>
            Production
          </button>
        </div>
        <p className="text-[9px] text-gray-500 break-all">{url}</p>
      </div>

      {/* QR Canvas */}
      <div className="flex justify-center">
        <div className="bg-white p-4 rounded-2xl inline-block">
          <canvas ref={canvasRef} className="block" />
          <p className="text-[9px] text-[#9CA3AF] text-center mt-2 font-bold tracking-widest uppercase">S2T Fitness Studio</p>
        </div>
      </div>

      <button onClick={downloadQR}
        className="w-full bg-[#4ADE80] text-[#111827] font-bold py-3 rounded-full hover:bg-[#3be074] transition-all flex items-center justify-center space-x-2 cursor-pointer text-sm">
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
        <span>Download QR as PNG</span>
      </button>
    </div>
  );
}
