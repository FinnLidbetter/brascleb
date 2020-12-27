import java.io.*;
import java.util.*;

public class ParseDictionary {
  public static void main(String[] args) throws IOException {
    BufferedReader br = new BufferedReader(new InputStreamReader(System.in));
    StringBuilder sb = new StringBuilder();

    String line = br.readLine();
    while (line!=null) {
      if (line.toLowerCase().equals(line) && line.length()<=15) {
        sb.append(line+"\n");
      }

      line = br.readLine();
    }
    System.out.print(sb);
  }
}
