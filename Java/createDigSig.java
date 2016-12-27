public class pkcs12 {
    private KeyStore getKeys(String fileName, String passwd) {
        try {
            KeyStore inStore = KeyStore.getInstance("PKCS12");
            inStore.load(new FileInputStream(fileName), passwd.toCharArray());

            return inStore;
        } catch(Exception e1) {
            e1.printStackTrace();
        }
        return null;
    }

    public String sign(String data, String key, String passwd) {
        try {
            KeyStore pkcs12Store = this.getKeys(key, passwd);
            PrivateKey privateKey = (PrivateKey) pkcs12Store.getKey(pkcs12Store.aliases().nextElement(), passwd.toCharArray());
            Signature sigEngine = Signature.getInstance("SHA256withRSA");

            sigEngine.initSign(privateKey);
            sigEngine.update(data.getBytes());

            byte[] signedData = sigEngine.sign();
            String signed = Base64.encodeToString(signedData, Base64.NO_WRAP);
            Log.i("SHA256withRSA", signed);
            return signed;

        } catch (Exception e1) {
            e1.printStackTrace();
        }
        return null;
    }
}
/*
 Usage:
    pkcs12 signEngine = new pkcs12();
    signEngine.sign("msg", "priv_and_pub.p12", "pass123")
*/
