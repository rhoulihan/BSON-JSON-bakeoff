import java.sql.*;

public class TestDualityView {
    public static void main(String[] args) {
        String url = "jdbc:oracle:thin:system/G0_4w4y!@172.19.16.1:1521/FREEPDB1";

        try {
            Class.forName("oracle.jdbc.driver.OracleDriver");
            Connection conn = DriverManager.getConnection(url);
            conn.setAutoCommit(false);

            Statement stmt = conn.createStatement();

            // Clear existing data
            System.out.println("Clearing existing data...");
            stmt.execute("DELETE FROM indexed_index_array");
            stmt.execute("DELETE FROM indexed_docs");
            conn.commit();

            // Test 1: Insert document with array via Duality View
            System.out.println("\nTest 1: Inserting 3 documents with overlapping array values via Duality View");
            String doc1 = "{\"_id\":\"test1\",\"data\":{\"x\":\"abc\"},\"indexArray\":[{\"value\":\"1\"},{\"value\":\"2\"},{\"value\":\"3\"}]}";
            String doc2 = "{\"_id\":\"test2\",\"data\":{\"x\":\"def\"},\"indexArray\":[{\"value\":\"2\"},{\"value\":\"3\"},{\"value\":\"4\"}]}";
            String doc3 = "{\"_id\":\"test3\",\"data\":{\"x\":\"ghi\"},\"indexArray\":[{\"value\":\"3\"},{\"value\":\"4\"},{\"value\":\"5\"}]}";

            PreparedStatement pstmt = conn.prepareStatement("INSERT INTO indexed_dv VALUES (?)");
            pstmt.setString(1, doc1);
            pstmt.executeUpdate();
            conn.commit();
            System.out.println("Inserted doc1");

            pstmt.setString(1, doc2);
            pstmt.executeUpdate();
            conn.commit();
            System.out.println("Inserted doc2");

            pstmt.setString(1, doc3);
            pstmt.executeUpdate();
            conn.commit();
            System.out.println("Inserted doc3");

            // Check what was inserted
            ResultSet rs = stmt.executeQuery("SELECT doc_id, COUNT(*) FROM indexed_index_array GROUP BY doc_id ORDER BY doc_id");
            System.out.println("\nArray elements per document:");
            while (rs.next()) {
                System.out.println("  " + rs.getString(1) + ": " + rs.getInt(2) + " elements");
            }

            rs = stmt.executeQuery("SELECT array_value, COUNT(*) FROM indexed_index_array GROUP BY array_value ORDER BY array_value");
            System.out.println("\nDocuments per array value:");
            while (rs.next()) {
                System.out.println("  value '" + rs.getString(1) + "': " + rs.getInt(2) + " documents");
            }

            rs = stmt.executeQuery("SELECT doc_id, array_value FROM indexed_index_array ORDER BY doc_id, array_value");
            System.out.println("\nAll array entries:");
            while (rs.next()) {
                System.out.println("  " + rs.getString(1) + " -> " + rs.getString(2));
            }

            conn.close();
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
