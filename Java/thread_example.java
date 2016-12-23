thread = new Thread(new Runnable() {

    @Override
    public void run() {
        try  {

        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public void send(String msg) {
        Log.i(TAG, "Sending message");
    }

});

thread.start();
