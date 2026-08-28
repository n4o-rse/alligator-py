package de.rgzm.alligator.functions;

import de.rgzm.alligator.classes.AlligatorEvent;
import java.util.HashMap;
import org.json.simple.JSONArray;

public class MatrixAllen {

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
            HashMap dm = thisEvent.allenRelations;
            for (String id2 : alligator.eventIDs) {
                if ("null".equals(String.valueOf(dm.get(id2)))) {
                    arrTmp.add("");
                } else {
                    arrTmp.add(String.valueOf(dm.get(id2)));
                }

            }
            arr.add(arrTmp);
        }
        return arr;
    }

}
