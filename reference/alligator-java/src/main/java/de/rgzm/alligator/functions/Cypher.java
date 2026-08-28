package de.rgzm.alligator.functions;

import de.rgzm.alligator.classes.AlligatorEvent;
import java.util.HashMap;
import java.util.StringJoiner;

public class Cypher {

    public static String writeCypher(Alligator alligator) {
        StringBuilder cypher = new StringBuilder();
        StringJoiner joiner = new StringJoiner(",");
        for (Object event : alligator.events) {
            AlligatorEvent ae = (AlligatorEvent) event;
            cypher.append("CREATE (" + ae.id + ":Event{label: '" + ae.name + "'})" + "\r\n");
            joiner.add(ae.id);
        }
        for (String id : alligator.eventIDs) {
            AlligatorEvent thisEvent = alligator.getEventById(id);
            HashMap dm = thisEvent.allenRelations;
            for (String id2 : alligator.eventIDs) {
                if (String.valueOf(dm.get(id2)) != "null") {
                    String allen = String.valueOf(dm.get(id2));
                    allen = allen.replace("<", "BEFORE");
                    allen = allen.replace(">", "AFTER");
                    allen = allen.replace("m", "MEETS");
                    allen = allen.replace("mi", "MET_BY");
                    allen = allen.replace("o", "OVERLAPS");
                    allen = allen.replace("oi", "OVERLAPPED_BY");
                    allen = allen.replace("s", "STARTS");
                    allen = allen.replace("si", "STARTED_BY");
                    allen = allen.replace("f", "FINISHES");
                    allen = allen.replace("fi", "FINISHED_BY");
                    allen = allen.replace("d", "DURING");
                    allen = allen.replace("di", "CONTAINS");
                    allen = allen.replace("=", "EQUALS");
                    cypher.append("MERGE (" + thisEvent.id + ")-[:" + allen + "]->(" + id2 + ")" + "\r\n");
                }
            }
        }
        cypher.append("RETURN " + joiner.toString());
        return cypher.toString();
    }

}
