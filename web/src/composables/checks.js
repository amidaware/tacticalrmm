
import { ref, onMounted } from "vue"
import { updateCheck, saveCheck } from "@/api/checks"
import { fetchAgentChecks } from "@/api/agents";
import { fetchPolicyChecks } from "@/api/automation";
import { formatCheckOptions } from "@/utils/format";
import { fetchAgent } from "@/api/agents"
import { isValidThreshold } from "@/utils/validation";
import { notifySuccess } from "@/utils/notify"

// for check add/edit modals
// pass as an object {editCheck: props.check, initialState: {default form values for adding check} }
export function useCheckModal({ editCheck, initialState }) {

  const check = editCheck
    ? ref(Object.assign({}, editCheck))
    : ref(initialState);

  const loading = ref(false)

  // save check function
  async function submit(onOk) {
    if (check.value.check_type === "cpuload" || check.value.check_type === "memory") {
      if (!isValidThreshold(check.value.warning_threshold, check.value.error_threshold)) return;
    }
    else if (check.value.check_type === "diskspace") {
      if (!isValidThreshold(check.value.warning_threshold, check.value.error_threshold, true)) return;
    }

    loading.value = true;
    try {
      const result = editCheck ? await updateCheck(check.value.id, check.value) : await saveCheck(check.value);
      notifySuccess(result);
      onOk();
    } catch (e) {
      console.error(e);
    }
    loading.value = false;
  }

  // dropdown options
  const failOptions = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

  const severityOptions = [
    { label: "Informational", value: "info" },
    { label: "Warning", value: "warning" },
    { label: "Error", value: "error" },
  ]

  const logNameOptions = ["Application", "System", "Security"]
  const failWhenOptions = [
    { label: "Log contains", value: "contains" },
    { label: "Log does not contain", value: "not_contains" },
  ]

  const diskOptions = ref('A:,B:,C:,D:,E:,F:,G:,H:,I:,J:,K:,L:,M:,N:,O:,P:,Q:,R:,S:,T:,U:,V:,W:,X:,Y:,Z:'.split(','))

  const serviceOptions = ref(Object.freeze(defaultServiceOptions))

  async function getAgentDiskOptions() {
    const { disks } = await fetchAgent(check.value.agent)
    diskOptions.value = disks.map(disk => disk.device)
    check.value.disk = diskOptions.value[0]
  }

  async function getAgentServiceOptions() {
    const { services } = await fetchAgent(check.value.agent)

    const tmp = services.map(service => ({ label: service.display_name, value: service.name }))
    serviceOptions.value = Object.freeze(tmp.sort((a, b) => a.label.localeCompare(b.label)))
    check.value.svc_name = serviceOptions.value[0].value
    check.value.svc_display_name = serviceOptions.value[0].label
  }

  onMounted(async () => {
    if (!editCheck && check.value.check_type === "diskspace" && check.value.agent) {
      await getAgentDiskOptions()
    }

    else if (!editCheck && check.value.check_type === "winsvc" && check.value.agent) {
      await getAgentServiceOptions()
    }
  })

  return {
    //data
    state: check,
    loading,
    failOptions,
    diskOptions,
    logNameOptions,
    failWhenOptions,
    severityOptions,
    serviceOptions,

    // methods
    submit
  }
}

export function useCheckDropdown() {
  const check = ref(null)
  const checks = ref([])
  const checkOptions = ref([])

  async function getCheckOptions({ agent, policy }, flat = false) {
    if (!agent && !policy) {
      console.error("Need to specify agent or policy object when calling getCheckOptions")
      return
    }
    checkOptions.value = formatCheckOptions(agent ? await fetchAgentChecks(agent) : await fetchPolicyChecks(policy), flat)
  }

  return {
    //data
    check,
    checks,
    checkOptions,

    //methods
    getCheckOptions
  }
}


export const defaultServiceOptions = [
  {
    value: "AJRouter",
    label: "AllJoyn Router Service"
  },
  {
    value: "ALG",
    label: "Application Layer Gateway Service"
  },
  {
    value: "AppIDSvc",
    label: "Application Identity"
  },
  {
    value: "Appinfo",
    label: "Application Information"
  },
  {
    value: "AppMgmt",
    label: "Application Management"
  },
  {
    value: "AppReadiness",
    label: "App Readiness"
  },
  {
    value: "AppVClient",
    label: "Microsoft App-V Client"
  },
  {
    value: "AppXSvc",
    label: "AppX Deployment Service (AppXSVC)"
  },
  {
    value: "AssignedAccessManagerSvc",
    label: "AssignedAccessManager Service"
  },
  {
    value: "atashost",
    label: "WebEx Service Host for Support Center"
  },
  {
    value: "AudioEndpointBuilder",
    label: "Windows Audio Endpoint Builder"
  },
  {
    value: "Audiosrv",
    label: "Windows Audio"
  },
  {
    value: "autotimesvc",
    label: "Cellular Time"
  },
  {
    value: "AxInstSV",
    label: "ActiveX Installer (AxInstSV)"
  },
  {
    value: "BDESVC",
    label: "BitLocker Drive Encryption Service"
  },
  {
    value: "BFE",
    label: "Base Filtering Engine"
  },
  {
    value: "BITS",
    label: "Background Intelligent Transfer Service"
  },
  {
    value: "Bonjour Service",
    label: "Bonjour Service"
  },
  {
    value: "BrokerInfrastructure",
    label: "Background Tasks Infrastructure Service"
  },
  {
    value: "BTAGService",
    label: "Bluetooth Audio Gateway Service"
  },
  {
    value: "BthAvctpSvc",
    label: "AVCTP service"
  },
  {
    value: "bthserv",
    label: "Bluetooth Support Service"
  },
  {
    value: "camsvc",
    label: "Capability Access Manager Service"
  },
  {
    value: "CDPSvc",
    label: "Connected Devices Platform Service"
  },
  {
    value: "CertPropSvc",
    label: "Certificate Propagation"
  },
  {
    value: "ClipSVC",
    label: "Client License Service (ClipSVC)"
  },
  {
    value: "COMSysApp",
    label: "COM+ System Application"
  },
  {
    value: "CoreMessagingRegistrar",
    label: "CoreMessaging"
  },
  {
    value: "cphs",
    label: "Intel(R) Content Protection HECI Service"
  },
  {
    value: "cplspcon",
    label: "Intel(R) Content Protection HDCP Service"
  },
  {
    value: "CryptSvc",
    label: "Cryptographic Services"
  },
  {
    value: "CscService",
    label: "Offline Files"
  },
  {
    value: "DcomLaunch",
    label: "DCOM Server Process Launcher"
  },
  {
    value: "defragsvc",
    label: "Optimize drives"
  },
  {
    value: "DeviceAssociationService",
    label: "Device Association Service"
  },
  {
    value: "DeviceInstall",
    label: "Device Install Service"
  },
  {
    value: "DevQueryBroker",
    label: "DevQuery Background Discovery Broker"
  },
  {
    value: "Dhcp",
    label: "DHCP Client"
  },
  {
    value: "diagnosticshub.standardcollector.service",
    label: "Microsoft (R) Diagnostics Hub Standard Collector Service"
  },
  {
    value: "diagsvc",
    label: "Diagnostic Execution Service"
  },
  {
    value: "DiagTrack",
    label: "Connected User Experiences and Telemetry"
  },
  {
    value: "DispBrokerDesktopSvc",
    label: "Display Policy Service"
  },
  {
    value: "DisplayEnhancementService",
    label: "Display Enhancement Service"
  },
  {
    value: "DmEnrollmentSvc",
    label: "Device Management Enrollment Service"
  },
  {
    value: "dmwappushservice",
    label: "Device Management Wireless Application Protocol (WAP) Push message Routing Service"
  },
  {
    value: "Dnscache",
    label: "DNS Client"
  },
  {
    value: "DoSvc",
    label: "Delivery Optimization"
  },
  {
    value: "dot3svc",
    label: "Wired AutoConfig"
  },
  {
    value: "DPS",
    label: "Diagnostic Policy Service"
  },
  {
    value: "DsmSvc",
    label: "Device Setup Manager"
  },
  {
    value: "DsSvc",
    label: "Data Sharing Service"
  },
  {
    value: "DusmSvc",
    label: "Data Usage"
  },
  {
    value: "Eaphost",
    label: "Extensible Authentication Protocol"
  },
  {
    value: "EFS",
    label: "Encrypting File System (EFS)"
  },
  {
    value: "embeddedmode",
    label: "Embedded Mode"
  },
  {
    value: "EntAppSvc",
    label: "Enterprise App Management Service"
  },
  {
    value: "EventLog",
    label: "Windows Event Log"
  },
  {
    value: "EventSystem",
    label: "COM+ Event System"
  },
  {
    value: "Fax",
    label: "Fax"
  },
  {
    value: "fdPHost",
    label: "Function Discovery Provider Host"
  },
  {
    value: "FDResPub",
    label: "Function Discovery Resource Publication"
  },
  {
    value: "fhsvc",
    label: "File History Service"
  },
  {
    value: "FontCache",
    label: "Windows Font Cache Service"
  },
  {
    value: "FrameServer",
    label: "Windows Camera Frame Server"
  },
  {
    value: "GoogleChromeElevationService",
    label: "Google Chrome Elevation Service"
  },
  {
    value: "gpsvc",
    label: "Group Policy Client"
  },
  {
    value: "GraphicsPerfSvc",
    label: "GraphicsPerfSvc"
  },
  {
    value: "hidserv",
    label: "Human Interface Device Service"
  },
  {
    value: "hns",
    label: "Host Network Service"
  },
  {
    value: "HvHost",
    label: "HV Host Service"
  },
  {
    value: "ibtsiva",
    label: "Intel Bluetooth Service"
  },
  {
    value: "icssvc",
    label: "Windows Mobile Hotspot Service"
  },
  {
    value: "IKEEXT",
    label: "IKE and AuthIP IPsec Keying Modules"
  },
  {
    value: "InstallService",
    label: "Microsoft Store Install Service"
  },
  {
    value: "iphlpsvc",
    label: "IP Helper"
  },
  {
    value: "IpxlatCfgSvc",
    label: "IP Translation Configuration Service"
  },
  {
    value: "KeyIso",
    label: "CNG Key Isolation"
  },
  {
    value: "KtmRm",
    label: "KtmRm for Distributed Transaction Coordinator"
  },
  {
    value: "LanmanServer",
    label: "Server"
  },
  {
    value: "LanmanWorkstation",
    label: "Workstation"
  },
  {
    value: "lfsvc",
    label: "Geolocation Service"
  },
  {
    value: "LicenseManager",
    label: "Windows License Manager Service"
  },
  {
    value: "lltdsvc",
    label: "Link-Layer Topology Discovery Mapper"
  },
  {
    value: "lmhosts",
    label: "TCP/IP NetBIOS Helper"
  },
  {
    value: "LSM",
    label: "Local Session Manager"
  },
  {
    value: "LxpSvc",
    label: "Language Experience Service"
  },
  {
    value: "LxssManager",
    label: "LxssManager"
  },
  {
    value: "MapsBroker",
    label: "Downloaded Maps Manager"
  },
  {
    value: "mpssvc",
    label: "Windows Defender Firewall"
  },
  {
    value: "MSDTC",
    label: "Distributed Transaction Coordinator"
  },
  {
    value: "MSiSCSI",
    label: "Microsoft iSCSI Initiator Service"
  },
  {
    value: "msiserver",
    label: "Windows Installer"
  },
  {
    value: "NaturalAuthentication",
    label: "Natural Authentication"
  },
  {
    value: "NcaSvc",
    label: "Network Connectivity Assistant"
  },
  {
    value: "NcbService",
    label: "Network Connection Broker"
  },
  {
    value: "NcdAutoSetup",
    label: "Network Connected Devices Auto-Setup"
  },
  {
    value: "Net Driver HPZ12",
    label: "Net Driver HPZ12"
  },
  {
    value: "Netlogon",
    label: "Netlogon"
  },
  {
    value: "Netman",
    label: "Network Connections"
  },
  {
    value: "netprofm",
    label: "Network List Service"
  },
  {
    value: "NetSetupSvc",
    label: "Network Setup Service"
  },
  {
    value: "NetTcpPortSharing",
    label: "Net.Tcp Port Sharing Service"
  },
  {
    value: "NgcCtnrSvc",
    label: "Microsoft Passport Container"
  },
  {
    value: "NgcSvc",
    label: "Microsoft Passport"
  },
  {
    value: "NlaSvc",
    label: "Network Location Awareness"
  },
  {
    value: "nsi",
    label: "Network Store Interface Service"
  },
  {
    value: "nvagent",
    label: "Network Virtualization Service"
  },
  {
    value: "OpenVPNService",
    label: "OpenVPNService"
  },
  {
    value: "OpenVPNServiceInteractive",
    label: "OpenVPN Interactive Service"
  },
  {
    value: "OpenVPNServiceLegacy",
    label: "OpenVPN Legacy Service"
  },
  {
    value: "ose64",
    label: "Office 64 Source Engine"
  },
  {
    value: "p2pimsvc",
    label: "Peer Networking Identity Manager"
  },
  {
    value: "p2psvc",
    label: "Peer Networking Grouping"
  },
  {
    value: "PcaSvc",
    label: "Program Compatibility Assistant Service"
  },
  {
    value: "PeerDistSvc",
    label: "BranchCache"
  },
  {
    value: "perceptionsimulation",
    label: "Windows Perception Simulation Service"
  },
  {
    value: "PerfHost",
    label: "Performance Counter DLL Host"
  },
  {
    value: "PhoneSvc",
    label: "Phone Service"
  },
  {
    value: "pla",
    label: "Performance Logs & Alerts"
  },
  {
    value: "PlugPlay",
    label: "Plug and Play"
  },
  {
    value: "Pml Driver HPZ12",
    label: "Pml Driver HPZ12"
  },
  {
    value: "PNRPAutoReg",
    label: "PNRP Machine Name Publication Service"
  },
  {
    value: "PNRPsvc",
    label: "Peer Name Resolution Protocol"
  },
  {
    value: "PolicyAgent",
    label: "IPsec Policy Agent"
  },
  {
    value: "Power",
    label: "Power"
  },
  {
    value: "PrintNotify",
    label: "Printer Extensions and Notifications"
  },
  {
    value: "ProfSvc",
    label: "User Profile Service"
  },
  {
    value: "PushToInstall",
    label: "Windows PushToInstall Service"
  },
  {
    value: "QWAVE",
    label: "Quality Windows Audio Video Experience"
  },
  {
    value: "RasAuto",
    label: "Remote Access Auto Connection Manager"
  },
  {
    value: "RasMan",
    label: "Remote Access Connection Manager"
  },
  {
    value: "RemoteAccess",
    label: "Routing and Remote Access"
  },
  {
    value: "RemoteRegistry",
    label: "Remote Registry"
  },
  {
    value: "RetailDemo",
    label: "Retail Demo Service"
  },
  {
    value: "RmSvc",
    label: "Radio Management Service"
  },
  {
    value: "RpcEptMapper",
    label: "RPC Endpoint Mapper"
  },
  {
    value: "RpcLocator",
    label: "Remote Procedure Call (RPC) Locator"
  },
  {
    value: "RpcSs",
    label: "Remote Procedure Call (RPC)"
  },
  {
    value: "SamSs",
    label: "Security Accounts Manager"
  },
  {
    value: "SCardSvr",
    label: "Smart Card"
  },
  {
    value: "ScDeviceEnum",
    label: "Smart Card Device Enumeration Service"
  },
  {
    value: "Schedule",
    label: "Task Scheduler"
  },
  {
    value: "SCPolicySvc",
    label: "Smart Card Removal Policy"
  },
  {
    value: "SDRSVC",
    label: "Windows Backup"
  },
  {
    value: "seclogon",
    label: "Secondary Logon"
  },
  {
    value: "SecurityHealthService",
    label: "Windows Security Service"
  },
  {
    value: "SEMgrSvc",
    label: "Payments and NFC/SE Manager"
  },
  {
    value: "SENS",
    label: "System Event Notification Service"
  },
  {
    value: "Sense",
    label: "Windows Defender Advanced Threat Protection Service"
  },
  {
    value: "SensorDataService",
    label: "Sensor Data Service"
  },
  {
    value: "SensorService",
    label: "Sensor Service"
  },
  {
    value: "SensrSvc",
    label: "Sensor Monitoring Service"
  },
  {
    value: "SessionEnv",
    label: "Remote Desktop Configuration"
  },
  {
    value: "SgrmBroker",
    label: "System Guard Runtime Monitor Broker"
  },
  {
    value: "SharedAccess",
    label: "Internet Connection Sharing (ICS)"
  },
  {
    value: "SharedRealitySvc",
    label: "Spatial Data Service"
  },
  {
    value: "ShellHWDetection",
    label: "Shell Hardware Detection"
  },
  {
    value: "shpamsvc",
    label: "Shared PC Account Manager"
  },
  {
    value: "smphost",
    label: "Microsoft Storage Spaces SMP"
  },
  {
    value: "SmsRouter",
    label: "Microsoft Windows SMS Router Service."
  },
  {
    value: "SNMPTRAP",
    label: "SNMP Trap"
  },
  {
    value: "spectrum",
    label: "Windows Perception Service"
  },
  {
    value: "Spooler",
    label: "Print Spooler"
  },
  {
    value: "sppsvc",
    label: "Software Protection"
  },
  {
    value: "SSDPSRV",
    label: "SSDP Discovery"
  },
  {
    value: "ssh-agent",
    label: "OpenSSH Authentication Agent"
  },
  {
    value: "sshd",
    label: "OpenSSH SSH Server"
  },
  {
    value: "SstpSvc",
    label: "Secure Socket Tunneling Protocol Service"
  },
  {
    value: "StateRepository",
    label: "State Repository Service"
  },
  {
    value: "stisvc",
    label: "Windows Image Acquisition (WIA)"
  },
  {
    value: "StorSvc",
    label: "Storage Service"
  },
  {
    value: "svsvc",
    label: "Spot Verifier"
  },
  {
    value: "swprv",
    label: "Microsoft Software Shadow Copy Provider"
  },
  {
    value: "SynTPEnhService",
    label: "SynTPEnh Caller Service"
  },
  {
    value: "SysMain",
    label: "SysMain"
  },
  {
    value: "SystemEventsBroker",
    label: "System Events Broker"
  },
  {
    value: "TabletInputService",
    label: "Touch Keyboard and Handwriting Panel Service"
  },
  {
    value: "TapiSrv",
    label: "Telephony"
  },
  {
    value: "TermService",
    label: "Remote Desktop Services"
  },
  {
    value: "RDMS",
    label: "Remote Desktop Management"
  },
  {
    value: "TermServLicensing",
    label: "Remote Desktop Licensing"
  },
  {
    value: "TSGateway",
    label: "Remote Desktop Gateway"
  },
  {
    value: "Tssdis",
    label: "Remote Desktop Connection Broker"
  },
  {
    value: "MMS",
    label: "Acronis Managed Machine Service"
  },
  {
    value: "Themes",
    label: "Themes"
  },
  {
    value: "TieringEngineService",
    label: "Storage Tiers Management"
  },
  {
    value: "TimeBrokerSvc",
    label: "Time Broker"
  },
  {
    value: "TokenBroker",
    label: "Web Account Manager"
  },
  {
    value: "TrkWks",
    label: "Distributed Link Tracking Client"
  },
  {
    value: "TroubleshootingSvc",
    label: "Recommended Troubleshooting Service"
  },
  {
    value: "TrustedInstaller",
    label: "Windows Modules Installer"
  },
  {
    value: "tzautoupdate",
    label: "Auto Time Zone Updater"
  },
  {
    value: "UevAgentService",
    label: "User Experience Virtualization Service"
  },
  {
    value: "UmRdpService",
    label: "Remote Desktop Services UserMode Port Redirector"
  },
  {
    value: "upnphost",
    label: "UPnP Device Host"
  },
  {
    value: "UserManager",
    label: "User Manager"
  },
  {
    value: "UsoSvc",
    label: "Update Orchestrator Service"
  },
  {
    value: "VacSvc",
    label: "Volumetric Audio Compositor Service"
  },
  {
    value: "VaultSvc",
    label: "Credential Manager"
  },
  {
    value: "vds",
    label: "Virtual Disk"
  },
  {
    value: "vmcompute",
    label: "Hyper-V Host Compute Service"
  },
  {
    value: "vmicguestinterface",
    label: "Hyper-V Guest Service Interface"
  },
  {
    value: "vmicheartbeat",
    label: "Hyper-V Heartbeat Service"
  },
  {
    value: "vmickvpexchange",
    label: "Hyper-V Data Exchange Service"
  },
  {
    value: "vmicrdv",
    label: "Hyper-V Remote Desktop Virtualization Service"
  },
  {
    value: "vmicshutdown",
    label: "Hyper-V Guest Shutdown Service"
  },
  {
    value: "vmictimesync",
    label: "Hyper-V Time Synchronization Service"
  },
  {
    value: "vmicvmsession",
    label: "Hyper-V PowerShell Direct Service"
  },
  {
    value: "vmicvss",
    label: "Hyper-V Volume Shadow Copy Requestor"
  },
  {
    value: "VSS",
    label: "Volume Shadow Copy"
  },
  {
    value: "W32Time",
    label: "Windows Time"
  },
  {
    value: "WaaSMedicSvc",
    label: "Windows Update Medic Service"
  },
  {
    value: "WalletService",
    label: "WalletService"
  },
  {
    value: "WarpJITSvc",
    label: "WarpJITSvc"
  },
  {
    value: "wbengine",
    label: "Block Level Backup Engine Service"
  },
  {
    value: "WbioSrvc",
    label: "Windows Biometric Service"
  },
  {
    value: "Wcmsvc",
    label: "Windows Connection Manager"
  },
  {
    value: "wcncsvc",
    label: "Windows Connect Now - Config Registrar"
  },
  {
    value: "WdiServiceHost",
    label: "Diagnostic Service Host"
  },
  {
    value: "WdiSystemHost",
    label: "Diagnostic System Host"
  },
  {
    value: "WdNisSvc",
    label: "Windows Defender Antivirus Network Inspection Service"
  },
  {
    value: "WebClient",
    label: "WebClient"
  },
  {
    value: "Wecsvc",
    label: "Windows Event Collector"
  },
  {
    value: "WEPHOSTSVC",
    label: "Windows Encryption Provider Host Service"
  },
  {
    value: "wercplsupport",
    label: "Problem Reports and Solutions Control Panel Support"
  },
  {
    value: "WerSvc",
    label: "Windows Error Reporting Service"
  },
  {
    value: "WFDSConMgrSvc",
    label: "Wi-Fi Direct Services Connection Manager Service"
  },
  {
    value: "WiaRpc",
    label: "Still Image Acquisition Events"
  },
  {
    value: "WinDefend",
    label: "Windows Defender Antivirus Service"
  },
  {
    value: "WinHttpAutoProxySvc",
    label: "WinHTTP Web Proxy Auto-Discovery Service"
  },
  {
    value: "Winmgmt",
    label: "Windows Management Instrumentation"
  },
  {
    value: "WinRM",
    label: "Windows Remote Management (WS-Management)"
  },
  {
    value: "wisvc",
    label: "Windows Insider Service"
  },
  {
    value: "WlanSvc",
    label: "WLAN AutoConfig"
  },
  {
    value: "wlidsvc",
    label: "Microsoft Account Sign-in Assistant"
  },
  {
    value: "wlpasvc",
    label: "Local Profile Assistant Service"
  },
  {
    value: "WManSvc",
    label: "Windows Management Service"
  },
  {
    value: "wmiApSrv",
    label: "WMI Performance Adapter"
  },
  {
    value: "WMPNetworkSvc",
    label: "Windows Media Player Network Sharing Service"
  },
  {
    value: "workfolderssvc",
    label: "Work Folders"
  },
  {
    value: "WpcMonSvc",
    label: "Parental Controls"
  },
  {
    value: "WPDBusEnum",
    label: "Portable Device Enumerator Service"
  },
  {
    value: "WpnService",
    label: "Windows Push Notifications System Service"
  },
  {
    value: "wscsvc",
    label: "Security Center"
  },
  {
    value: "WSearch",
    label: "Windows Search"
  },
  {
    value: "wuauserv",
    label: "Windows Update"
  },
  {
    value: "WwanSvc",
    label: "WWAN AutoConfig"
  },
  {
    value: "XblAuthManager",
    label: "Xbox Live Auth Manager"
  },
  {
    value: "XblGameSave",
    label: "Xbox Live Game Save"
  },
  {
    value: "XboxGipSvc",
    label: "Xbox Accessory Management Service"
  },
  {
    value: "XboxNetApiSvc",
    label: "Xbox Live Networking Service"
  },
  {
    value: "YMC",
    label: "YMC"
  },
  {
    value: "AarSvc_35b28a",
    label: "Agent Activation Runtime_35b28a"
  },
  {
    value: "BcastDVRUserService_35b28a",
    label: "GameDVR and Broadcast User Service_35b28a"
  },
  {
    value: "BluetoothUserService_35b28a",
    label: "Bluetooth User Support Service_35b28a"
  },
  {
    value: "CaptureService_35b28a",
    label: "CaptureService_35b28a"
  },
  {
    value: "cbdhsvc_35b28a",
    label: "Clipboard User Service_35b28a"
  },
  {
    value: "CDPUserSvc_35b28a",
    label: "Connected Devices Platform User Service_35b28a"
  },
  {
    value: "ConsentUxUserSvc_35b28a",
    label: "ConsentUX_35b28a"
  },
  {
    value: "CredentialEnrollmentManagerUserSvc_35b28a",
    label: "CredentialEnrollmentManagerUserSvc_35b28a"
  },
  {
    value: "DeviceAssociationBrokerSvc_35b28a",
    label: "DeviceAssociationBroker_35b28a"
  },
  {
    value: "DevicePickerUserSvc_35b28a",
    label: "DevicePicker_35b28a"
  },
  {
    value: "DevicesFlowUserSvc_35b28a",
    label: "DevicesFlow_35b28a"
  },
  {
    value: "LxssManagerUser_35b28a",
    label: "LxssManagerUser_35b28a"
  },
  {
    value: "MessagingService_35b28a",
    label: "MessagingService_35b28a"
  },
  {
    value: "OneSyncSvc_35b28a",
    label: "Sync Host_35b28a"
  },
  {
    value: "PimIndexMaintenanceSvc_35b28a",
    label: "Contact Data_35b28a"
  },
  {
    value: "PrintWorkflowUserSvc_35b28a",
    label: "PrintWorkflow_35b28a"
  },
  {
    value: "UnistoreSvc_35b28a",
    label: "User Data Storage_35b28a"
  },
  {
    value: "UserDataSvc_35b28a",
    label: "User Data Access_35b28a"
  },
  {
    value: "WpnUserService_35b28a",
    label: "Windows Push Notifications User Service_35b28a"
  },
  {
    value: "Mesh Agent",
    label: "Mesh Agent background service"
  },
  {
    value: "salt-minion",
    label: "salt-minion"
  },
  {
    value: "tacticalagent",
    label: "Tactical RMM Agent"
  }
].sort((a, b) => a.label.localeCompare(b.label))