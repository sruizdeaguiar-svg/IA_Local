"""Per-user filesystem protection and LAN TLS without macOS command dependencies."""
import process_runtime
from pathlib import Path
import datetime,hashlib,ipaddress,os,re,socket,subprocess

def secure_directory(path):
    """Restrict the data directory before credentials are created; fail closed."""
    path=Path(path);path.mkdir(parents=True,exist_ok=True)
    if os.name!='nt':path.chmod(0o700);return
    # Replace the complete DACL. Merely granting/removing inheritance can retain
    # explicit broad entries from a pre-existing temporary/user directory.
    result=process_runtime.run(['whoami','/user','/fo','csv','/nh'],capture_output=True,check=True)
    sid=re.search(rb'S-1-5-[0-9-]+',result.stdout)
    if not sid:raise RuntimeError('No se pudo identificar el usuario de Windows para proteger los datos.')
    import ctypes
    from ctypes import wintypes
    api=ctypes.windll.advapi32;kernel=ctypes.windll.kernel32
    descriptor=ctypes.c_void_p();dacl=ctypes.c_void_p();present=wintypes.BOOL();defaulted=wintypes.BOOL()
    sddl='D:P(A;OICI;FA;;;'+sid[0].decode('ascii')+')(A;OICI;FA;;;SY)'
    if not api.ConvertStringSecurityDescriptorToSecurityDescriptorW(ctypes.c_wchar_p(sddl),1,ctypes.byref(descriptor),None):raise OSError('No se pudo preparar la protección NTFS.')
    try:
        if not api.GetSecurityDescriptorDacl(descriptor,ctypes.byref(present),ctypes.byref(dacl),ctypes.byref(defaulted)) or not present.value:raise OSError('DACL NTFS no válida.')
        status=api.SetNamedSecurityInfoW(ctypes.c_wchar_p(str(path)),1,wintypes.DWORD(0x80000004),None,None,dacl,None)
        if status:raise OSError(status,'No se pudieron proteger los datos con permisos del usuario y SYSTEM.')
    finally:kernel.LocalFree(descriptor)

def certificate(root,ip):
    """Generate a private P-256 self-signed certificate; trust remains a user action."""
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes,serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    root=Path(root);cert=root/'lan-cert.pem';key=root/'lan-key.pem'
    hostname=re.sub('[^a-z0-9.-]','-',socket.gethostname().lower()).strip('.') or 'ia-local'
    if '.' not in hostname:hostname+='.local'
    if not cert.exists() or not key.exists():
        private=ec.generate_private_key(ec.SECP256R1());now=datetime.datetime.now(datetime.timezone.utc)
        subject=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,hostname)])
        public=(x509.CertificateBuilder().subject_name(subject).issuer_name(subject).public_key(private.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-datetime.timedelta(minutes=5)).not_valid_after(now+datetime.timedelta(days=365)).add_extension(x509.SubjectAlternativeName([x509.DNSName(hostname),x509.IPAddress(ipaddress.ip_address(ip))]),critical=False).add_extension(x509.BasicConstraints(ca=False,path_length=None),critical=True).sign(private,hashes.SHA256()))
        fd=os.open(key,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        with os.fdopen(fd,'wb') as f:f.write(private.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
        cert.write_bytes(public.public_bytes(serialization.Encoding.PEM));cert.chmod(0o644)
    public=x509.load_pem_x509_certificate(cert.read_bytes());digest=':'.join(f'{b:02X}' for b in public.fingerprint(hashes.SHA256()))
    return cert,key,hostname,digest
