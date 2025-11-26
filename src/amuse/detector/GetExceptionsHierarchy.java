
import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.security.NoSuchAlgorithmException;

import javax.crypto.NoSuchPaddingException;

public class GetExceptionsHierarchy {

    public static void main(String[] args) {
	    // write your code here

        try {
            String previousClass = args[0];
           Class exceptions = Class.forName(args[0]).getSuperclass();

            // Class exceptions = Class.forName("java.io.FileNotFoundException");
//             && exceptions.getTypeName() != "java.lang.Object"
            while (exceptions != null) {
                System.out.print(previousClass.toString() + "\t" + exceptions.getName() + "\n");
                previousClass = exceptions.getName();

                exceptions = exceptions.getSuperclass();
            }
        } catch (ClassNotFoundException e) {
            e.printStackTrace();
        }

    }
}
