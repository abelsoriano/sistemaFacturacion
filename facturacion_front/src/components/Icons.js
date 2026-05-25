import React from 'react';

export const IconArrowLeft = ({ width = 13, height = 13, stroke = 'currentColor', strokeWidth = 2, ...props }) => (
  <svg width={width} height={height} fill="none" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24" {...props}>
    <line x1="19" y1="12" x2="5" y2="12" />
    <polyline points="12 19 5 12 12 5" />
  </svg>
);

export const IconSearch = ({ width = 13, height = 13, stroke = 'currentColor', strokeWidth = 2, ...props }) => (
  <svg width={width} height={height} fill="none" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24" {...props}>
    <circle cx="11" cy="11" r="8" />
    <line x1="21" y1="21" x2="16.65" y2="16.65" />
  </svg>
);

export const IconX = ({ width = 12, height = 12, stroke = 'currentColor', strokeWidth = 2.5, ...props }) => (
  <svg width={width} height={height} fill="none" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" viewBox="0 0 24 24" {...props}>
    <line x1="18" y1="6" x2="6" y2="18" />
    <line x1="6" y1="6" x2="18" y2="18" />
  </svg>
);

export const IconPlus = ({ width = 13, height = 13, stroke = 'currentColor', strokeWidth = 2, ...props }) => (
  <svg width={width} height={height} fill="none" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" viewBox="0 0 24 24" {...props}>
    <line x1="12" y1="5" x2="12" y2="19" />
    <line x1="5" y1="12" x2="19" y2="12" />
  </svg>
);

export const IconExcel = ({ width = 13, height = 13, stroke = 'currentColor', strokeWidth = 2, ...props }) => (
  <svg width={width} height={height} fill="none" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24" {...props}>
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <polyline points="14 2 14 8 20 8" />
    <line x1="9" y1="13" x2="15" y2="13" />
    <line x1="9" y1="17" x2="15" y2="17" />
  </svg>
);

export const IconEye = ({ width = 13, height = 13, stroke = 'currentColor', strokeWidth = 2, ...props }) => (
  <svg width={width} height={height} fill="none" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24" {...props}>
    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
    <circle cx="12" cy="12" r="3" />
  </svg>
);

export const IconEdit = ({ width = 13, height = 13, stroke = 'currentColor', strokeWidth = 2, ...props }) => (
  <svg width={width} height={height} fill="none" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24" {...props}>
    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
  </svg>
);

export const IconTrash = ({ width = 13, height = 13, stroke = 'currentColor', strokeWidth = 2, ...props }) => (
  <svg width={width} height={height} fill="none" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24" {...props}>
    <polyline points="3 6 5 6 21 6" />
    <path d="M19 6l-1 14H6L5 6" />
    <path d="M10 11v6M14 11v6" />
    <path d="M9 6V4h6v2" />
  </svg>
);

export const IconChevLeft = ({ width = 12, height = 12, stroke = 'currentColor', strokeWidth = 2, ...props }) => (
  <svg width={width} height={height} fill="none" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24" {...props}>
    <polyline points="15 18 9 12 15 6" />
  </svg>
);

export const IconChevRight = ({ width = 12, height = 12, stroke = 'currentColor', strokeWidth = 2, ...props }) => (
  <svg width={width} height={height} fill="none" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24" {...props}>
    <polyline points="9 18 15 12 9 6" />
  </svg>
);

export const IconReceipt = ({ width = 16, height = 16, stroke = '#1D9E75', strokeWidth = 2, ...props }) => (
  <svg width={width} height={height} fill="none" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24" {...props}>
    <path d="M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1-2-1-2 1z" />
    <line x1="9" y1="7" x2="15" y2="7" />
    <line x1="9" y1="11" x2="15" y2="11" />
  </svg>
);

export const IconRefresh = ({ width = 13, height = 13, stroke = 'currentColor', strokeWidth = 2, ...props }) => (
  <svg width={width} height={height} fill="none" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24" {...props}>
    <polyline points="23 4 23 10 17 10" />
    <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
  </svg>
);

export const IconPDF = ({ width = 13, height = 13, stroke = 'currentColor', strokeWidth = 2, ...props }) => (
  <svg width={width} height={height} fill="none" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24" {...props}>
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <polyline points="14 2 14 8 20 8" />
    <line x1="9" y1="7" x2="15" y2="7" />
  </svg>
);

export const IconFilter = ({ width = 13, height = 13, stroke = 'currentColor', strokeWidth = 2, ...props }) => (
  <svg width={width} height={height} fill="none" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24" {...props}>
    <path d="M3 4h18M6 12h12M10 20h4" />
  </svg>
);

export const IconAlert = ({ width = 14, height = 14, stroke = 'currentColor', strokeWidth = 2, ...props }) => (
  <svg width={width} height={height} fill="none" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24" {...props}>
    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
    <line x1="12" y1="9" x2="12" y2="13" />
    <line x1="12" y1="17" x2="12.01" y2="17" />
  </svg>
);

export const IconFile = ({ width = 15, height = 15, stroke = 'currentColor', strokeWidth = 2, ...props }) => (
  <svg width={width} height={height} fill="none" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24" {...props}>
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <polyline points="14 2 14 8 20 8" />
    <line x1="16" y1="13" x2="8" y2="13" />
    <line x1="16" y1="17" x2="8" y2="17" />
  </svg>
);

export const IconChart = ({ width = 15, height = 15, stroke = 'currentColor', strokeWidth = 2, ...props }) => (
  <svg width={width} height={height} fill="none" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24" {...props}>
    <line x1="18" y1="20" x2="18" y2="10" />
    <line x1="12" y1="20" x2="12" y2="4" />
    <line x1="6" y1="20" x2="6" y2="14" />
  </svg>
);

export const IconBox = ({ width = 18, height = 18, stroke = 'currentColor', strokeWidth = 2, ...props }) => (
  <svg width={width} height={height} fill="none" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24" {...props}>
    <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
  </svg>
);

export const IconMinus = ({ width = 13, height = 13, stroke = 'currentColor', strokeWidth = 2.5, ...props }) => (
  <svg width={width} height={height} fill="none" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" viewBox="0 0 24 24" {...props}>
    <path d="M5 12h14" />
  </svg>
);

export const IconCart = ({ width = 16, height = 16, stroke = 'currentColor', strokeWidth = 2, ...props }) => (
  <svg width={width} height={height} fill="none" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" viewBox="0 0 24 24" {...props}>
    <circle cx="9" cy="21" r="1" />
    <circle cx="20" cy="21" r="1" />
    <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6" />
  </svg>
);

export const IconUser = ({ width = 14, height = 14, stroke = 'currentColor', strokeWidth = 2, ...props }) => (
  <svg width={width} height={height} fill="none" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24" {...props}>
    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
    <circle cx="12" cy="7" r="4" />
  </svg>
);

export const IconUserPlus = ({ width = 14, height = 14, stroke = 'currentColor', strokeWidth = 2, ...props }) => (
  <svg width={width} height={height} fill="none" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24" {...props}>
    <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
    <circle cx="9" cy="7" r="4" />
    <line x1="19" y1="8" x2="19" y2="14" />
    <line x1="16" y1="11" x2="22" y2="11" />
  </svg>
);

export const IconCheck = ({ width = 15, height = 15, stroke = 'currentColor', strokeWidth = 2.5, ...props }) => (
  <svg width={width} height={height} fill="none" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" viewBox="0 0 24 24" {...props}>
    <polyline points="20 6 9 17 4 12" />
  </svg>
);

export const IconDownload = ({ width = 13, height = 13, stroke = 'currentColor', strokeWidth = 2, ...props }) => (
  <svg width={width} height={height} fill="none" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24" {...props}>
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
    <polyline points="7 10 12 15 17 10" />
    <line x1="12" y1="15" x2="12" y2="3" />
  </svg>
);

export const IconPrint = ({ width = 13, height = 13, stroke = 'currentColor', strokeWidth = 2, ...props }) => (
  <svg width={width} height={height} fill="none" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24" {...props}>
    <polyline points="6 9 6 2 18 2 18 9" />
    <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2" />
    <rect x="6" y="14" width="12" height="8" />
  </svg>
);

export const IconClipboard = ({ width = 13, height = 13, stroke = 'currentColor', strokeWidth = 2, ...props }) => (
  <svg width={width} height={height} fill="none" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24" {...props}>
    <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" />
    <rect x="8" y="2" width="8" height="4" rx="1" />
  </svg>
);

export const IconBell = ({ width = 15, height = 15, stroke = 'currentColor', strokeWidth = 2, ...props }) => (
  <svg width={width} height={height} fill="none" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24" {...props}>
    <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
    <path d="M13.73 21a2 2 0 0 1-3.46 0" />
  </svg>
);

export const IconChevron = ({ width = 12, height = 12, stroke = 'currentColor', strokeWidth = 2, ...props }) => (
  <svg width={width} height={height} fill="none" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24" {...props}>
    <polyline points="6 9 12 15 18 9" />
  </svg>
);

export const IconCog = ({ width = 14, height = 14, stroke = 'currentColor', strokeWidth = 2, ...props }) => (
  <svg width={width} height={height} fill="none" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24" {...props}>
    <circle cx="12" cy="12" r="3" />
    <path d="M19.07 4.93a10 10 0 0 1 0 14.14M4.93 4.93a10 10 0 0 0 0 14.14" />
  </svg>
);

export const IconLogout = ({ width = 14, height = 14, stroke = 'currentColor', strokeWidth = 2, ...props }) => (
  <svg width={width} height={height} fill="none" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24" {...props}>
    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
    <polyline points="16 17 21 12 16 7" />
    <line x1="21" y1="12" x2="9" y2="12" />
  </svg>
);

export const IconTag = ({ width = 18, height = 18, stroke = 'currentColor', strokeWidth = 2, ...props }) => (
  <svg width={width} height={height} fill="none" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24" {...props}>
    <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z" />
    <line x1="7" y1="7" x2="7.01" y2="7" />
  </svg>
);

export const IconWarehouse = ({ width = 18, height = 18, stroke = 'currentColor', strokeWidth = 2, ...props }) => (
  <svg width={width} height={height} fill="none" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24" {...props}>
    <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
    <polyline points="9 22 9 12 15 12 15 22" />
  </svg>
);

export const IconBolt = ({ width = 18, height = 18, stroke = 'currentColor', strokeWidth = 2, ...props }) => (
  <svg width={width} height={height} fill="none" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24" {...props}>
    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
  </svg>
);

export const IconInvoice = ({ width = 18, height = 18, stroke = 'currentColor', strokeWidth = 2, ...props }) => (
  <svg width={width} height={height} fill="none" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24" {...props}>
    <path d="M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1-2-1-2 1z" />
    <line x1="9" y1="7" x2="15" y2="7" />
    <line x1="9" y1="11" x2="15" y2="11" />
  </svg>
);

export const IconTools = ({ width = 18, height = 18, stroke = 'currentColor', strokeWidth = 2, ...props }) => (
  <svg width={width} height={height} fill="none" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24" {...props}>
    <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
  </svg>
);

export const IconBuilding = ({ width = 18, height = 18, stroke = 'currentColor', strokeWidth = 2, ...props }) => (
  <svg width={width} height={height} fill="none" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24" {...props}>
    <rect x="2" y="7" width="20" height="14" rx="2" />
    <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
  </svg>
);

export const IconUsers = ({ width = 14, height = 14, stroke = 'currentColor', strokeWidth = 2, ...props }) => (
  <svg width={width} height={height} fill="none" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24" {...props}>
    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
    <circle cx="9" cy="7" r="4" />
    <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
    <path d="M16 3.13a4 4 0 0 1 0 7.75" />
  </svg>
);

export const IconReport = ({ width = 14, height = 14, stroke = 'currentColor', strokeWidth = 2, ...props }) => (
  <svg width={width} height={height} fill="none" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24" {...props}>
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <polyline points="14 2 14 8 20 8" />
    <line x1="16" y1="13" x2="8" y2="13" />
    <line x1="16" y1="17" x2="8" y2="17" />
  </svg>
);

export const IconDashboard = ({ width = 14, height = 14, stroke = 'currentColor', strokeWidth = 2, ...props }) => (
  <svg width={width} height={height} fill="none" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24" {...props}>
    <rect x="3" y="3" width="7" height="7" />
    <rect x="14" y="3" width="7" height="7" />
    <rect x="14" y="14" width="7" height="7" />
    <rect x="3" y="14" width="7" height="7" />
  </svg>
);
