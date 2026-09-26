import { useEffect, useState } from 'react';

import { getBranches } from '../api/profile';
import { StateView } from '../components/StateView';
import type { Branch } from '../types/api';

export function BranchesPage() {
  const [branches, setBranches] = useState<Branch[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    getBranches()
      .then((response) => setBranches(response.results))
      .catch((caught: unknown) => setError(caught instanceof Error ? caught.message : 'Не удалось загрузить филиалы'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <StateView title="Загрузка..." description="Получаем филиалы." />;
  }

  if (error) {
    return <StateView title="Не удалось загрузить данные" description={error} />;
  }

  return (
    <section className="page">
      <h1>Филиалы</h1>
      {branches.length === 0 ? (
        <StateView title="Нет филиалов" description="Активные филиалы пока не добавлены." />
      ) : (
        <div className="list">
          {branches.map((branch) => (
            <article className="list-item" key={branch.id}>
              <strong>{branch.name}</strong>
              <span>{branch.address}</span>
              {branch.phone ? <small>{branch.phone}</small> : null}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
