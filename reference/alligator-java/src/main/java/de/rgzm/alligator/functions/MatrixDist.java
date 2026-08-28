package de.rgzm.alligator.functions;

import de.rgzm.alligator.classes.AlligatorEvent;
import java.text.DecimalFormat;
import java.util.HashMap;
import org.json.simple.JSONArray;

public class MatrixDist {
    
    public static JSONArray writeMatrixAsJSONArray(Alligator alligator) {
        JSONArray arr = new JSONArray();
        JSONArray arrHeader = new JSONArray();
        arrHeader.add("");
        for (String id : alligator.eventIDs) {
            arrHeader.add(alligator.getEventById(id).name);
        }
        arr.add(arrHeader);
        for (String id : alligator.eventIDs) {
            JSONArray arrTmp = new JSONArray();
            arrTmp.add(alligator.getEventById(id).name);
            AlligatorEvent thisEvent = alligator.getEventById(id);
            HashMap dm = thisEvent.distances;
            for (String id2 : alligator.eventIDs) {
                DecimalFormat df = new DecimalFormat("0.0000");
                arrTmp.add(String.valueOf(df.format(dm.get(id2))));
            }
            arr.add(arrTmp);
        }
        return arr;
    }
    
}
