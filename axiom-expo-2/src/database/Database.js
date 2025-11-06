import { openDatabase } from 'expo-sqlite';

const db = openDatabase('Axiom.db');

export const initDatabase = () => {
  db.transaction(tx => {
    tx.executeSql(
      'CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, password TEXT, address TEXT);'
    );
  });
};

export const addUser = (name, password, address) => {
  return new Promise((resolve, reject) => {
    db.transaction(tx => {
      tx.executeSql(
        'INSERT INTO users (name, password, address) VALUES (?, ?, ?);',
        [name, password, address],
        (_, result) => {
          resolve(result);
        },
        (_, error) => {
          reject(error);
        }
      );
    });
  });
};

export const findUser = (name, password) => {
  return new Promise((resolve, reject) => {
    db.transaction(tx => {
      tx.executeSql(
        'SELECT * FROM users WHERE name = ? AND password = ?;',
        [name, password],
        (_, { rows }) => {
          if (rows.length > 0) {
            resolve(rows._array[0]);
          } else {
            resolve(null);
          }
        },
        (_, error) => {
          reject(error);
        }
      );
    });
  });
};
