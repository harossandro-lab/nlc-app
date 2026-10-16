import com.nlc.materiallist.calc.CalcEngine;
import com.nlc.materiallist.model.TakeoffItem;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;

/**
 * Reads one test case per line from stdin (tab separated: purpose, length, lf, sf, sp, ea, material, species),
 * prints "qty<TAB>parsedLength<TAB>itemKey" for each, using the Java CalcEngine. Used only by tests/test_parity_java.py.
 */
public class QtyParity {
    static Double num(String s) { return s.isEmpty() ? null : Double.valueOf(s); }

    public static void main(String[] args) throws Exception {
        String tab = String.valueOf((char) 9);
        BufferedReader in = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8));
        StringBuilder out = new StringBuilder();
        String line;
        while ((line = in.readLine()) != null) {
            String[] f = line.split(tab, -1);
            TakeoffItem t = new TakeoffItem();
            t.purpose = f[0]; t.length = f[1]; t.lf = num(f[2]); t.sf = num(f[3]); t.sp = f[4]; t.ea = num(f[5]);
            t.material = f[6]; t.species = f[7];
            Integer qty = CalcEngine.computeQty(t);
            Double len = CalcEngine.parseLength(f[1]);
            out.append(qty == null ? "null" : qty.toString()).append(tab)
               .append(len == null ? "null" : len.toString()).append(tab)
               .append(CalcEngine.itemKeyOf(t)).append('\n');
        }
        System.out.print(out);
    }
}
