#Privacy

- Nothing in this code tracks you or calls into any server but OneDrive.
- All communications to OneDrive are encrypted with HTTPS. ParanoidDrive will throw an error if something is wrong with the cert.
- All files uploaded to OneDrive are encrypted with AES-256 (on top of whatever OneDrive uses internally).

**DISCLAIMER:** I am no cryptographer. Don't trust your super important secrets on my code that probably has some issues. (Speaking of issues, report one if you find it!)
