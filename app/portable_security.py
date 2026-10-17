"""Per-user filesystem protection and LAN TLS without macOS command dependencies."""
import process_runtime
from pathlib import Path
import datetime,hashlib,ipaddress,os,re,socket,subprocess

def secure_directory(path):
    """Restrict the data directory before credentials are created; fail closed."""
    path=Path(path);path.mkdir(parents=True,exist_ok=True)
    if os.name!='nt':path.chmod(0o700);return
    # An explicit SID avoids localization and ambiguous domain/user account names.
    result=process_runtime.run(['whoami','/user','/fo','csv','/nh'],capture_output=True,text=True,check=True)
    sid=re.search(r'S-1-5-[0-9-]+',result.stdout)
    if not sid:raise RuntimeError('No se pudo identificar el usuario de Windows para proteger los datos.')
    process_runtime.run(['icacls',str(path),'/inheritance:r','/grant:r','*'+sid[0]+':(OI)(CI)F','*S-1-5-18:(OI)(CI)F'],capture_output=True,check=True)

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
